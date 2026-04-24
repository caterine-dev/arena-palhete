from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.models import db, Reserva, ContratoMensalista, Cliente, Configuracao
from datetime import datetime, time, timedelta

agenda_bp = Blueprint('agenda', __name__, url_prefix='/agenda')

@agenda_bp.route('/')
@login_required
def index():
    data_str = request.args.get('data', datetime.now().strftime('%Y-%m-%d'))
    data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
    
    # Variáveis de navegação blindadas
    data_anterior = (data_selecionada - timedelta(days=1)).strftime('%Y-%m-%d')
    data_seguinte = (data_selecionada + timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Puxa o horário de funcionamento real do painel de Ajustes!
    hora_abertura = int(Configuracao.get('hora_abertura', '8'))
    hora_fechamento = int(Configuracao.get('hora_fechamento', '23'))
    
    # Busca as reservas do dia
    reservas = Reserva.query.filter_by(data=data_selecionada).filter(Reserva.status != 'cancelada').all()
    
    return render_template('agenda/index.html', 
                           reservas=reservas, 
                           data_selecionada=data_selecionada,
                           data_anterior=data_anterior,
                           data_seguinte=data_seguinte,
                           hora_abertura=hora_abertura,
                           hora_fechamento=hora_fechamento)

@agenda_bp.route('/verificar-disponibilidade')
@login_required
def verificar_disponibilidade():
    data_str = request.args.get('data')
    inicio_str = request.args.get('inicio')
    fim_str = request.args.get('fim')
    if not all([data_str, inicio_str, fim_str]):
        return jsonify({'disponivel': False})
    data = datetime.strptime(data_str, '%Y-%m-%d').date()
    h_ini = datetime.strptime(inicio_str, '%H:%M').time()
    h_fim = datetime.strptime(fim_str, '%H:%M').time()
    conflito = Reserva.query.filter(Reserva.data == data, Reserva.status != 'cancelada',
                                    Reserva.hora_inicio < h_fim, Reserva.hora_fim > h_ini).first()
    return jsonify({'disponivel': conflito is None})

@agenda_bp.route('/<int:reserva_id>/iniciar', methods=['POST'])
@login_required
def iniciar(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    reserva.status = 'em andamento'
    db.session.commit()
    flash('Partida iniciada!', 'success')
    return redirect(url_for('agenda.index', data=reserva.data.strftime('%Y-%m-%d')))

@agenda_bp.route('/<int:reserva_id>/finalizar', methods=['POST'])
@login_required
def finalizar(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    reserva.status = 'finalizada'
    db.session.commit()
    flash('Partida finalizada!', 'success')
    return redirect(url_for('agenda.index', data=reserva.data.strftime('%Y-%m-%d')))

@agenda_bp.route('/<int:reserva_id>/cancelar', methods=['POST'])
@login_required
def cancelar(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    reserva.status = 'cancelada'
    db.session.commit()
    flash('Reserva cancelada.', 'success')
    return redirect(url_for('agenda.index', data=reserva.data.strftime('%Y-%m-%d')))

# --- NOVA ROTA: RECEBER PAGAMENTO PENDENTE ---
@agenda_bp.route('/<int:reserva_id>/cobrar', methods=['POST'])
@login_required
def cobrar(reserva_id):
    reserva = Reserva.query.get_or_404(reserva_id)
    if reserva.pagamento:
        reserva.pagamento.status = 'pago'
        db.session.commit()
        flash('Pagamento recebido e registrado no Financeiro!', 'success')
    return redirect(url_for('agenda.index', data=reserva.data.strftime('%Y-%m-%d')))