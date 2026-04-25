from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.models import db, ContratoMensalista, Cliente, Pagamento, PlanoMensalista, Reserva
from datetime import datetime, timedelta

mensalistas_bp = Blueprint('mensalistas', __name__, url_prefix='/mensalistas')

@mensalistas_bp.route('/')
@login_required
def index():
    filtro = request.args.get('filtro', 'todos')
    hoje = datetime.now()
    mes, ano = hoje.month, hoje.year

    contratos = ContratoMensalista.query.filter(
        ContratoMensalista.cliente_id.isnot(None), 
        ContratoMensalista.status == 'ativo'
    ).all()

    resultado = []
    for c in contratos:
        pagamento = c.mensalidade_mes(mes, ano)
        status_pgto = 'pago' if pagamento and pagamento.status == 'pago' else 'pendente'
        
        if filtro == 'ativos' and status_pgto != 'pago': continue
        if filtro == 'pendentes' and status_pgto != 'pendente': continue
            
        resultado.append({'contrato': c, 'status_pgto': status_pgto})

    return render_template('mensalistas/index.html', resultado=resultado, filtro=filtro, mes=mes, ano=ano)


# --- NOVA ROTA: O MOTOR DO TEMPO (CRIAR MENSALISTA) ---
@mensalistas_bp.route('/novo', methods=['GET', 'POST'])
@login_required
def novo():
    if request.method == 'POST':
        # 1. Puxa todos os dados preenchidos na tela
        cliente_id = request.form.get('cliente_id')
        plano_id = request.form.get('plano_id')
        dia_semana_escolhido = int(request.form.get('dia_semana'))
        hora_inicio_str = request.form.get('hora_inicio')
        data_inicio_str = request.form.get('data_inicio')
        data_fim_str = request.form.get('data_fim')

        # 2. Busca o plano para saber quantos minutos dura a quadra
        plano = PlanoMensalista.query.get(plano_id)
        
        # Converte as horas e calcula a hora exata do fim
        h, m = map(int, hora_inicio_str.split(':'))
        inicio_dt = datetime.combine(datetime.today(), datetime.min.time()).replace(hour=h, minute=m)
        fim_dt = inicio_dt + timedelta(minutes=plano.duracao_minutos)
        
        hora_inicio_time = inicio_dt.time()
        hora_fim_time = fim_dt.time()

        # 3. Cria o "Contrato Guarda-Chuva" no banco de dados
        novo_contrato = ContratoMensalista(
            cliente_id=cliente_id,
            plano_id=plano_id,
            dia_semana=dia_semana_escolhido,
            hora_inicio=hora_inicio_time,
            hora_fim=hora_fim_time,
            status='ativo'
        )
        db.session.add(novo_contrato)
        db.session.flush() # Salva temporariamente para gerar o ID do contrato

        # 4. Transforma as datas de texto para 'Datas do Python'
        data_atual = datetime.strptime(data_inicio_str, '%Y-%m-%d').date()
        data_final = datetime.strptime(data_fim_str, '%Y-%m-%d').date()

        # Inteligência: Se a 'Data Início' escolhida não cair no 'Dia da Semana Fixo', 
        # o Python pula os dias automaticamente até achar o dia certo para começar.
        while data_atual.weekday() != dia_semana_escolhido:
            data_atual += timedelta(days=1)

        # 5. O LOOP: Viaja no tempo criando uma reserva a cada 7 dias até o fim do ano (data_final)
        while data_atual <= data_final:
            nova_reserva = Reserva(
                cliente_id=cliente_id,
                data=data_atual,
                hora_inicio=hora_inicio_time,
                hora_fim=hora_fim_time,
                tipo='mensalista',
                status='confirmada'
            )
            db.session.add(nova_reserva)
            
            # A Mágica: Pula 7 dias exatos para a frente!
            data_atual += timedelta(days=7)

        # 6. Grava todas as dezenas de reservas na agenda de uma vez só
        db.session.commit()
        flash('Contrato gerado e reservas distribuídas na agenda com sucesso!', 'success')
        return redirect(url_for('mensalistas.index'))

    # Se for apenas para carregar a tela (GET)
    clientes = Cliente.query.all()
    planos = PlanoMensalista.query.all()
    return render_template('mensalistas/novo.html', clientes=clientes, planos=planos)


@mensalistas_bp.route('/cobrar/<int:contrato_id>', methods=['POST'])
@login_required
def cobrar(contrato_id):
    contrato = ContratoMensalista.query.get_or_404(contrato_id)
    hoje = datetime.now()
    pagamento = Pagamento(cliente_id=contrato.cliente_id, contrato_id=contrato.id, tipo='mensalidade',
                          valor=contrato.plano.valor_mensal, forma='pix', status='pago',
                          mes_referencia=f"{hoje.year}-{hoje.month:02d}")
    db.session.add(pagamento)
    db.session.commit()
    flash(f'Pagamento de {contrato.cliente.nome} registrado!', 'success')
    return redirect(url_for('mensalistas.index'))

# --- ROTAS DE MANUTENÇÃO ---

@mensalistas_bp.route('/<int:contrato_id>/editar', methods=['GET', 'POST'])
@login_required
def editar(contrato_id):
    contrato = ContratoMensalista.query.get_or_404(contrato_id)
    planos = PlanoMensalista.query.all()

    if request.method == 'POST':
        contrato.plano_id = request.form.get('plano_id')
        contrato.frequencia = request.form.get('frequencia')
        contrato.dia_semana = request.form.get('dia_semana')
        hora_inicio_str = request.form.get('hora_inicio')
        hora_fim_str = request.form.get('hora_fim')

        if hora_inicio_str and hora_fim_str:
            contrato.hora_inicio = datetime.strptime(hora_inicio_str, '%H:%M').time()
            contrato.hora_fim = datetime.strptime(hora_fim_str, '%H:%M').time()

        db.session.commit()
        flash('Contrato atualizado com sucesso!', 'success')
        # Volta para a ficha do cliente usando a nossa rota blindada
        return redirect(f"/clientes/{contrato.cliente_id}")

    return render_template('mensalistas/editar.html', contrato=contrato, planos=planos)


@mensalistas_bp.route('/<int:contrato_id>/cancelar', methods=['POST'])
@login_required
def cancelar(contrato_id):
    contrato = ContratoMensalista.query.get_or_404(contrato_id)
    # Regra de Ouro: Nunca deletar. Apenas mudar o status para liberar a agenda!
    contrato.status = 'cancelado' 
    db.session.commit()
    flash('Plano cancelado com sucesso. A quadra foi liberada.', 'success')
    return redirect(f"/clientes/{contrato.cliente_id}")