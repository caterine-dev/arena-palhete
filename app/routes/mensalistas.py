from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models import db, Cliente, ContratoMensalista, PlanoMensalista, Pagamento, Reserva
import datetime as dt

mensalistas_bp = Blueprint('mensalistas', __name__, url_prefix='/mensalistas')

DIAS_SEMANA = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']


@mensalistas_bp.route('/')
@login_required
def index():
    filtro = request.args.get('filtro', 'todos')
    hoje = date.today()
    mes, ano = hoje.month, hoje.year

    contratos = ContratoMensalista.query.filter_by(status='ativo').all()

    resultado = []
    for c in contratos:
        pgto = c.mensalidade_mes(mes, ano)
        status_pgto = pgto.status if pgto else 'pendente'
        if filtro == 'ativos' or filtro == 'todos':
            resultado.append({'contrato': c, 'status_pgto': status_pgto})
        elif filtro == 'pendentes' and status_pgto == 'pendente':
            resultado.append({'contrato': c, 'status_pgto': status_pgto})

    if filtro == 'ativos':
        resultado = [r for r in resultado]

    return render_template('mensalistas/index.html',
                           resultado=resultado,
                           filtro=filtro,
                           dias_semana=DIAS_SEMANA,
                           mes=mes, ano=ano)


@mensalistas_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    planos = PlanoMensalista.query.all()
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id', type=int)
        plano_id = request.form.get('plano_id', type=int)
        dia_semana = request.form.get('dia_semana', type=int)
        hora_inicio_str = request.form.get('hora_inicio')

        try:
            h, m = map(int, hora_inicio_str.split(':'))
            hora_inicio = dt.time(h, m)
        except Exception:
            flash('Horário inválido.', 'error')
            return render_template('mensalistas/novo.html', planos=planos, dias_semana=DIAS_SEMANA)

        # Verifica conflito de horário no dia da semana
        plano = PlanoMensalista.query.get(plano_id)
        hora_fim = (dt.datetime.combine(date.today(), hora_inicio) +
                    dt.timedelta(minutes=plano.duracao_minutos)).time()

        conflito = ContratoMensalista.query.filter_by(
            dia_semana=dia_semana, status='ativo'
        ).filter(
            ContratoMensalista.hora_inicio < hora_fim,
        ).first()

        if conflito:
            flash(f'Horário conflita com contrato de {conflito.cliente.nome}.', 'error')
            return render_template('mensalistas/novo.html', planos=planos, dias_semana=DIAS_SEMANA)

        # Atualiza tipo do cliente
        cliente = Cliente.query.get_or_404(cliente_id)
        cliente.tipo = 'mensalista'

        contrato = ContratoMensalista(
            cliente_id=cliente_id,
            plano_id=plano_id,
            dia_semana=dia_semana,
            hora_inicio=hora_inicio,
            data_inicio=date.today(),
        )
        db.session.add(contrato)
        db.session.commit()

        flash(f'Mensalista {cliente.nome} cadastrado com sucesso!', 'success')
        return redirect(url_for('mensalistas.index'))

    return render_template('mensalistas/novo.html', planos=planos, dias_semana=DIAS_SEMANA)


@mensalistas_bp.route('/cobrar/<int:contrato_id>', methods=['POST'])
@login_required
def cobrar(contrato_id):
    contrato = ContratoMensalista.query.get_or_404(contrato_id)
    hoje = date.today()
    mes, ano = hoje.month, hoje.year
    mes_ref = f'{ano}-{mes:02d}'
    forma = request.form.get('forma', 'dinheiro')

    pgto_existente = contrato.mensalidade_mes(mes, ano)
    if pgto_existente:
        pgto_existente.status = 'pago'
        pgto_existente.forma = forma
    else:
        pgto = Pagamento(
            cliente_id=contrato.cliente_id,
            contrato_id=contrato_id,
            tipo='mensalidade',
            valor=contrato.plano.valor_mensal,
            forma=forma,
            status='pago',
            mes_referencia=mes_ref,
        )
        db.session.add(pgto)

    db.session.commit()
    flash(f'Mensalidade de {contrato.cliente.nome} registrada como paga.', 'success')
    return redirect(request.referrer or url_for('mensalistas.index'))


@mensalistas_bp.route('/inativar/<int:contrato_id>', methods=['POST'])
@login_required
def inativar(contrato_id):
    if not current_user.is_gerente():
        flash('Acesso restrito ao gerente.', 'error')
        return redirect(url_for('mensalistas.index'))
    contrato = ContratoMensalista.query.get_or_404(contrato_id)
    contrato.status = 'inativo'
    contrato.data_fim = date.today()
    contrato.cliente.tipo = 'avulso'
    db.session.commit()
    flash('Contrato encerrado.', 'info')
    return redirect(url_for('mensalistas.index'))
