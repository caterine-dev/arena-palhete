from datetime import date, datetime, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.models import db, Cliente, Reserva, Pagamento, PlanoMensalista, ContratoMensalista, Configuracao
from app.services.google_calendar import criar_evento

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
        tipo = request.form.get('tipo', 'avulso')

        if not nome or not telefone:
            flash('Nome e telefone são obrigatórios.', 'error')
            return redirect(url_for('clientes.novo'))

        cliente = Cliente(nome=nome, telefone=telefone, tipo=tipo)
        db.session.add(cliente)
        db.session.flush()

        if tipo in ['mensalista', 'quinzenalista']:
            plano_id = request.form.get('plano_id')
            dia_semana = request.form.get('dia_semana')
            hora_inicio_str = request.form.get('hora_inicio')
            hora_fim_str = request.form.get('hora_fim')
            data_inicio_str = request.form.get('data_inicio')
            data_fim_str = request.form.get('data_fim')

            if not all([plano_id, dia_semana, hora_inicio_str, hora_fim_str, data_inicio_str, data_fim_str]):
                db.session.rollback()
                flash('Preencha todos os dados do plano e as datas de início e fim.', 'error')
                return redirect(url_for('clientes.novo'))

            hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
            hora_fim = datetime.strptime(hora_fim_str, '%H:%M').time()
            dia_semana_int = int(dia_semana)

            contrato = ContratoMensalista(
                cliente_id=cliente.id,
                plano_id=plano_id,
                frequencia=tipo,
                dia_semana=dia_semana_int,
                hora_inicio=hora_inicio,
                hora_fim=hora_fim,
                status='ativo'
            )
            db.session.add(contrato)

            # --- MOTOR DO TEMPO COM SINCRONIZAÇÃO GOOGLE ---
            data_atual = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
            data_final = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

            while data_atual.weekday() != dia_semana_int:
                data_atual += timedelta(days=1)

            pulo = 14 if tipo == 'quinzenalista' else 7

            while data_atual <= data_final:
                nova_reserva = Reserva(
                    cliente_id=cliente.id,
                    data=data_atual,
                    hora_inicio=hora_inicio,
                    hora_fim=hora_fim,
                    tipo=tipo,
                    status='confirmada'
                )
                db.session.add(nova_reserva)
                
                # NOVO: Envia para o Google Agenda individualmente
                try:
                    criar_evento(nova_reserva, nome)
                except Exception as e:
                    print(f"Erro ao sincronizar reserva recorrente: {e}")
                
                data_atual += timedelta(days=pulo)
            # -----------------------------------------------

        try:
            db.session.commit()
            flash(f'Cadastro de {nome} realizado com sucesso! Agenda e Google sincronizados.', 'success')
            return redirect(url_for('agenda.index'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao salvar no banco de dados.', 'error')
            return redirect(url_for('clientes.novo'))

    planos = PlanoMensalista.query.all()
    return render_template('clientes/novo.html', planos=planos)

@clientes_bp.route('/<int:cliente_id>')
@login_required
def ficha(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    reservas = Reserva.query.filter_by(cliente_id=cliente_id).order_by(Reserva.data.desc()).limit(30).all()
    contrato = None
    if cliente.tipo in ['mensalista', 'quinzenalista'] and cliente.contratos:
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

@clientes_bp.route('/reserva/nova', methods=['GET', 'POST'])
@login_required
def nova_reserva():
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id', type=int)
        if not cliente_id:
            flash('Selecione um cliente.', 'error')
            return redirect(url_for('clientes.nova_reserva'))
        
        data_str = request.form.get('data')
        inicio_str = request.form.get('hora_inicio')
        fim_str = request.form.get('hora_fim')
        valor_str = request.form.get('valor', '0').replace(',', '.')
        valor = float(valor_str)
        forma = request.form.get('forma_pagamento')
        status_pgto = request.form.get('status_pagamento', 'pago')

        from datetime import time, date as ddate
        data = ddate.fromisoformat(data_str)
        hora_inicio = datetime.strptime(inicio_str, '%H:%M').time()
        hora_fim = datetime.strptime(fim_str, '%H:%M').time()

        reserva = Reserva(
            cliente_id=cliente_id,
            data=data,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            tipo='avulso',
            status='confirmada'
        )
        db.session.add(reserva)
        db.session.flush()

        pagamento = Pagamento(
            cliente_id=cliente_id,
            reserva_id=reserva.id,
            tipo='avulso',
            valor=valor,
            forma=forma,
            status=status_pgto
        )
        db.session.add(pagamento)
        db.session.commit()

        try:
            cliente_nome = Cliente.query.get(cliente_id).nome
            criar_evento(reserva, cliente_nome)
        except Exception as e:
            print(f"Erro na integração: {e}")

        flash('Reserva criada com sucesso!', 'success')
        return redirect(url_for('agenda.index', data=data_str))

    cliente_id = request.args.get('cliente_id', type=int)
    cliente = Cliente.query.get(cliente_id) if cliente_id else None
    
    configs = {
        'valor_1h': Configuracao.get('valor_avulso_1h', '150.00'),
        'valor_1h30': Configuracao.get('valor_avulso_1h30', '200.00'),
        'valor_2h': Configuracao.get('valor_avulso_2h', '250.00')
    }
    
    return render_template('clientes/nova_reserva.html', cliente=cliente, hoje=date.today(), configs=configs)