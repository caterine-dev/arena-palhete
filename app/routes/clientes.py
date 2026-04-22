from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.models import db, Cliente, Reserva, Pagamento

clientes_bp = Blueprint('clientes', __name__, url_prefix='/clientes')


@clientes_bp.route('/buscar')
@login_required
def buscar():
    q = request.args.get('q', '').strip()
    clientes = []
    if q:
        clientes = Cliente.query.filter(
            (Cliente.nome.ilike(f'%{q}%')) | (Cliente.telefone.ilike(f'%{q}%'))
        ).limit(10).all()
    return jsonify([{'id': c.id, 'nome': c.nome, 'telefone': c.telefone, 'tipo': c.tipo} for c in clientes])


@clientes_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        telefone = request.form.get('telefone', '').strip()
        if not nome or not telefone:
            flash('Nome e telefone são obrigatórios.', 'error')
            return render_template('clientes/novo.html')
        cliente = Cliente(nome=nome, telefone=telefone)
        db.session.add(cliente)
        db.session.commit()
        flash(f'Cliente {nome} cadastrado com sucesso!', 'success')
        return redirect(request.args.get('next') or url_for('clientes.ficha', cliente_id=cliente.id))
    return render_template('clientes/novo.html')


@clientes_bp.route('/<int:cliente_id>')
@login_required
def ficha(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    reservas = Reserva.query.filter_by(cliente_id=cliente_id).order_by(Reserva.data.desc()).limit(30).all()
    contrato = None
    if cliente.tipo == 'mensalista' and cliente.contratos:
        contrato = next((c for c in cliente.contratos if c.status == 'ativo'), None)

    hoje = date.today()
    mensalidade_mes = None
    if contrato:
        mensalidade_mes = contrato.mensalidade_mes(hoje.month, hoje.year)

    return render_template(
        'clientes/ficha.html',
        cliente=cliente,
        reservas=reservas,
        contrato=contrato,
        mensalidade_mes=mensalidade_mes,
        hoje=hoje,
    )


@clientes_bp.route('/<int:cliente_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    if request.method == 'POST':
        cliente.nome = request.form.get('nome', '').strip()
        cliente.telefone = request.form.get('telefone', '').strip()
        db.session.commit()
        flash('Dados atualizados.', 'success')
        return redirect(url_for('clientes.ficha', cliente_id=cliente_id))
    return render_template('clientes/editar.html', cliente=cliente)


# ── Reservas avulsas ──────────────────────────────────────────────────────────

@clientes_bp.route('/reserva/nova', methods=['GET', 'POST'])
@login_required
def nova_reserva():
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id', type=int)
        data_str = request.form.get('data')
        inicio_str = request.form.get('hora_inicio')
        fim_str = request.form.get('hora_fim')
        valor = request.form.get('valor', type=float)
        forma = request.form.get('forma_pagamento')
        status_pgto = request.form.get('status_pagamento', 'pago')
        observacoes = request.form.get('observacoes', '')

        from datetime import time, date as ddate
        try:
            data = ddate.fromisoformat(data_str)
            h_ini, m_ini = map(int, inicio_str.split(':'))
            h_fim, m_fim = map(int, fim_str.split(':'))
            hora_inicio = time(h_ini, m_ini)
            hora_fim = time(h_fim, m_fim)
        except Exception:
            flash('Data ou horário inválidos.', 'error')
            return redirect(url_for('clientes.nova_reserva'))

        # Verificar conflito
        conflito = Reserva.query.filter(
            Reserva.data == data,
            Reserva.status != 'cancelada',
            Reserva.hora_inicio < hora_fim,
            Reserva.hora_fim > hora_inicio,
        ).first()
        if conflito:
            flash(f'Horário conflita com reserva de {conflito.cliente.nome}.', 'error')
            return redirect(url_for('clientes.nova_reserva'))

        reserva = Reserva(
            cliente_id=cliente_id,
            data=data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            tipo='avulso',
            status='confirmada',
            observacoes=observacoes,
        )
        db.session.add(reserva)
        db.session.flush()

        pagamento = Pagamento(
            cliente_id=cliente_id,
            reserva_id=reserva.id,
            tipo='avulso',
            valor=valor,
            forma=forma,
            status=status_pgto,
        )
        db.session.add(pagamento)
        db.session.commit()

        flash('Reserva criada com sucesso!', 'success')
        return redirect(url_for('agenda.index', data=data_str))

    cliente_id = request.args.get('cliente_id', type=int)
    cliente = Cliente.query.get(cliente_id) if cliente_id else None
    return render_template('clientes/nova_reserva.html', cliente=cliente, hoje=date.today())
