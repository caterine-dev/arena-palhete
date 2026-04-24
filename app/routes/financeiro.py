from flask import Blueprint, render_template, request
from flask_login import login_required
from app.models import db, Reserva, Pagamento, ContratoMensalista, Configuracao
from datetime import datetime, timedelta, date

financeiro_bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')

@financeiro_bp.route('/')
@login_required
def index():
    periodo = request.args.get('periodo', 'semana')
    hoje = date.today()
    
    if periodo == 'mes':
        data_inicio = hoje.replace(day=1)
        prox_mes = data_inicio.replace(day=28) + timedelta(days=4)
        data_fim = prox_mes - timedelta(days=prox_mes.day)
    else: # semana
        data_inicio = hoje - timedelta(days=hoje.weekday())
        data_fim = data_inicio + timedelta(days=6)

    # 1. FATURAMENTO TOTAL E GRÁFICO (Lê Avulsos e Mensalistas)
    pagamentos = Pagamento.query.filter_by(status='pago').all()
    
    faturamento_total = 0
    total_mensalidades = 0
    total_avulsos = 0
    faturamento_dias = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    
    for p in pagamentos:
        data_pgto = hoje
        # Descobre a data correta para colocar no gráfico
        if p.reserva:
            data_pgto = p.reserva.data
        elif hasattr(p, 'criado_em') and p.criado_em:
            data_pgto = p.criado_em.date() if isinstance(p.criado_em, datetime) else p.criado_em
            
        if data_inicio <= data_pgto <= data_fim:
            faturamento_total += p.valor
            if p.tipo == 'mensalidade':
                total_mensalidades += p.valor
            else:
                total_avulsos += p.valor
            
            # Soma o valor no dia da semana correto (0=Segunda, 6=Domingo)
            faturamento_dias[data_pgto.weekday()] += float(p.valor)

    # 2. TOTAL DE RESERVAS E TAXA DE OCUPAÇÃO
    reservas = Reserva.query.filter(Reserva.data >= data_inicio, Reserva.data <= data_fim).all()
    reservas_validas = [r for r in reservas if r.status in ['confirmada', 'em andamento', 'finalizada']]
    total_reservas = len(reservas_validas)
    
    minutos_ocupados = sum(r.duracao_minutos() for r in reservas_validas)
    
    hora_abertura = int(Configuracao.get('hora_abertura', '8'))
    hora_fechamento = int(Configuracao.get('hora_fechamento', '23'))
    if hora_fechamento <= hora_abertura: 
        hora_fechamento = 23; hora_abertura = 8
        
    horas_por_dia = hora_fechamento - hora_abertura
    dias_no_periodo = (data_fim - data_inicio).days + 1
    minutos_totais = horas_por_dia * 60 * dias_no_periodo
    
    taxa_ocupacao = 0
    if minutos_totais > 0:
        taxa_ocupacao = (minutos_ocupados / minutos_totais) * 100
        if taxa_ocupacao > 100: taxa_ocupacao = 100
        if taxa_ocupacao < 0: taxa_ocupacao = 0

    # 3. PENDÊNCIAS
    mes_atual = f"{hoje.year}-{hoje.month:02d}"
    contratos_ativos = ContratoMensalista.query.filter_by(status='ativo').all()
    pendentes = []
    for c in contratos_ativos:
        pgto = Pagamento.query.filter_by(contrato_id=c.id, mes_referencia=mes_atual, status='pago').first()
        if not pgto:
            pendentes.append(c)

    return render_template('financeiro/index.html', 
                           faturamento_total=faturamento_total,
                           total_mensalidades=total_mensalidades,
                           total_avulsos=total_avulsos,
                           faturamento_dias=faturamento_dias,
                           total_reservas=total_reservas,
                           taxa_ocupacao=round(taxa_ocupacao, 1),
                           pendentes=pendentes,
                           periodo=periodo)