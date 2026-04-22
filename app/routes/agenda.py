from datetime import date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models import db, Reserva, Cliente, Pagamento, Configuracao

agenda_bp = Blueprint('agenda', __name__, url_prefix='/agenda')


@agenda_bp.route('/')
@login_required
def index():
    data_str = request.args.get('data')
    if data_str:
        try:
            data_selecionada = date.fromisoformat(data_str)
        except ValueError:
            data_selecionada = date.today()
    else:
        data_selecionada = date.today()

    reservas = Reserva.query.filter_by(data=data_selecionada).filter(
        Reserva.status != 'cancelada'
    ).order_by(Reserva.hora_inicio).all()

    hora_abertura = int(Configuracao.get('hora_abertura', '8'))
    hora_fechamento = int(Configuracao.get('hora_fechamento', '23'))

    return render_template(
        'agenda/index.html',
        reservas=reservas,
        data_selecionada=data_selecionada,
        data_anterior=data_selecionada - timedelta(days=1),
        data_seguinte=data_selecionada + timedelta(days=1),
        hora_abertura=hora_abertura,
        hora_fechamento=hora_fechamento,
    )


@agenda_bp.route('/encerrar/<int:reserva_id>', methods=['POST'])
@login_required
def encerrar(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    reserva.status = 'concluida'
    db.session.commit()
    flash('Reserva encerrada com sucesso.', 'success')
    return redirect(url_for('agenda.index', data=reserva.data.isoformat()))


@agenda_bp.route('/iniciar/<int:reserva_id>', methods=['POST'])
@login_required
def iniciar(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    reserva.status = 'em_andamento'
    db.session.commit()
    return redirect(url_for('agenda.index', data=reserva.data.isoformat()))


@agenda_bp.route('/cancelar/<int:reserva_id>', methods=['POST'])
@login_required
def cancelar(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    reserva.status = 'cancelada'
    db.session.commit()
    flash('Reserva cancelada.', 'info')
    return redirect(url_for('agenda.index', data=reserva.data.isoformat()))


@agenda_bp.route('/verificar-disponibilidade')
@login_required
def verificar_disponibilidade():
    """API endpoint para checar conflito de horário (anti double-booking)"""
    from datetime import time
    data_str = request.args.get('data')
    inicio_str = request.args.get('inicio')
    fim_str = request.args.get('fim')
    reserva_id = request.args.get('reserva_id', type=int)

    try:
        data = date.fromisoformat(data_str)
        h_ini, m_ini = map(int, inicio_str.split(':'))
        h_fim, m_fim = map(int, fim_str.split(':'))
        inicio = time(h_ini, m_ini)
        fim = time(h_fim, m_fim)
    except Exception:
        return jsonify({'disponivel': False, 'erro': 'Dados inválidos'})

    query = Reserva.query.filter(
        Reserva.data == data,
        Reserva.status != 'cancelada',
        Reserva.hora_inicio < fim,
        Reserva.hora_fim > inicio,
    )
    if reserva_id:
        query = query.filter(Reserva.id != reserva_id)

    conflito = query.first()
    return jsonify({'disponivel': conflito is None})
