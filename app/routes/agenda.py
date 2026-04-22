from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, Reserva, ContratoMensalista, Cliente
from datetime import datetime, time

bp = Blueprint('agenda', __name__, url_prefix='/agenda')

def verificar_conflito(data_reserva, hora_inicio, hora_fim):
    """
    Retorna True se houver conflito, False se o horário estiver livre.
    """
    # 1. Verificar conflito com outras reservas (avulsas ou mensalistas já lançadas)
    conflito_reserva = Reserva.query.filter(
        Reserva.data == data_reserva,
        Reserva.status != 'cancelada',
        Reserva.hora_inicio < hora_fim,
        Reserva.hora_fim > hora_inicio
    ).first()
    
    if conflito_reserva:
        return True, f"Já existe uma reserva para este horário ({conflito_reserva.cliente.nome})."

    # 2. Verificar conflito com Contratos de Mensalistas (horários fixos)
    dia_semana = data_reserva.weekday() # 0=Segunda, 1=Terça...
    conflito_contrato = ContratoMensalista.query.filter(
        ContratoMensalista.dia_semana == dia_semana,
        ContratoMensalista.status == 'ativo',
        ContratoMensalista.hora_inicio < hora_fim,
        ContratoMensalista.hora_fim > hora_inicio
    ).first()

    if conflito_contrato:
        return True, f"Este horário é reservado para o mensalista {conflito_contrato.cliente.nome}."

    return False, ""

@bp.route('/')
@login_required
def index():
    data_str = request.args.get('data', datetime.now().strftime('%Y-%m-%d'))
    data_selecionada = datetime.strptime(data_str, '%Y-%m-%d').date()
    
    # Busca reservas do dia para exibir no grid
    reservas = Reserva.query.filter_by(data=data_selecionada).order_by(Reserva.hora_inicio).all()
    
    return render_template('agenda/index.html', 
                           reservas=reservas, 
                           data_selecionada=data_selecionada)

@bp.route('/nova', methods=['GET', 'POST'])
@login_required
def nova_reserva():
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id')
        data_reserva = datetime.strptime(request.form.get('data'), '%Y-%m-%d').date()
        hora_inicio = datetime.strptime(request.form.get('hora_inicio'), '%H:%M').time()
        hora_fim = datetime.strptime(request.form.get('hora_fim'), '%H:%M').time()
        observacoes = request.form.get('observacoes')

        # Validar se o horário de início é antes do fim
        if hora_inicio >= hora_fim:
            flash('O horário de início deve ser anterior ao horário de término.', 'danger')
            return redirect(url_for('agenda.nova_reserva'))

        # Executar validação de conflitos
        tem_conflito, mensagem = verificar_conflito(data_reserva, hora_inicio, hora_fim)
        
        if tem_conflito:
            flash(mensagem, 'danger')
            return redirect(url_for('agenda.nova_reserva'))

        # Criar a reserva
        nova = Reserva(
            cliente_id=cliente_id,
            data=data_reserva,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            tipo='avulso',
            observacoes=observacoes
        )
        
        try:
            db.session.add(nova)
            db.session.commit()
            flash('Reserva realizada com sucesso!', 'success')
            return redirect(url_for('agenda.index', data=data_reserva))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao salvar reserva. Tente novamente.', 'danger')

    clientes = Cliente.query.order_by(Cliente.nome).all()
    return render_template('agenda/nova_reserva.html', clientes=clientes)