import csv
import io
from datetime import date, timedelta
from flask import Blueprint, render_template, request, Response
from flask_login import login_required, current_user
from sqlalchemy import func
from app.models import db, Pagamento, Reserva, ContratoMensalista, Configuracao

financeiro_bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')


def get_periodo(periodo, data_inicio_str, data_fim_str):
    hoje = date.today()
    if periodo == 'semana':
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
        fim = hoje
    elif periodo == 'personalizado' and data_inicio_str and data_fim_str:
        try:
            inicio = date.fromisoformat(data_inicio_str)
            fim = date.fromisoformat(data_fim_str)
        except ValueError:
            inicio = hoje.replace(day=1)
            fim = hoje
    else:
        inicio = hoje.replace(day=1)
        fim = hoje
    return inicio, fim


@financeiro_bp.route('/')
@login_required
def index():
    periodo = request.args.get('periodo', 'mes')
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    inicio, fim = get_periodo(periodo, data_inicio_str, data_fim_str)

    pagamentos = Pagamento.query.filter(
        Pagamento.criado_em >= inicio,
        Pagamento.criado_em <= fim,
        Pagamento.status == 'pago'
    ).all()

    faturamento_total = sum(p.valor for p in pagamentos)
    total_reservas = Reserva.query.filter(
        Reserva.data >= inicio, Reserva.data <= fim,
        Reserva.status != 'cancelada'
    ).count()

    # Taxa de ocupação
    hora_abertura = int(Configuracao.get('hora_abertura', '8'))
    hora_fechamento = int(Configuracao.get('hora_fechamento', '23'))
    horas_dia = hora_fechamento - hora_abertura
    dias_periodo = (fim - inicio).days + 1
    horas_totais = horas_dia * dias_periodo
    horas_ocupadas = sum(r.duracao_minutos() / 60 for r in Reserva.query.filter(
        Reserva.data >= inicio, Reserva.data <= fim,
        Reserva.status.in_(['confirmada', 'em_andamento', 'concluida'])
    ).all())
    taxa_ocupacao = round((horas_ocupadas / horas_totais * 100), 1) if horas_totais > 0 else 0

    # Mensalidades pendentes no mês atual
    hoje = date.today()
    contratos_ativos = ContratoMensalista.query.filter_by(status='ativo').all()
    pendentes = [c for c in contratos_ativos if not c.mensalidade_mes(hoje.month, hoje.year)
                 or c.mensalidade_mes(hoje.month, hoje.year).status == 'pendente']

    # Faturamento por dia da semana
    por_dia = {i: 0 for i in range(7)}
    for p in pagamentos:
        dia = p.criado_em.weekday()
        por_dia[dia] += p.valor

    # Avulso vs Mensalidade
    fat_avulso = sum(p.valor for p in pagamentos if p.tipo == 'avulso')
    fat_mensalidade = sum(p.valor for p in pagamentos if p.tipo == 'mensalidade')

    return render_template('financeiro/index.html',
                           faturamento_total=faturamento_total,
                           total_reservas=total_reservas,
                           taxa_ocupacao=taxa_ocupacao,
                           pendentes=pendentes,
                           por_dia=por_dia,
                           fat_avulso=fat_avulso,
                           fat_mensalidade=fat_mensalidade,
                           periodo=periodo,
                           inicio=inicio,
                           fim=fim,
                           hoje=hoje)


@financeiro_bp.route('/exportar-csv')
@login_required
def exportar_csv():
    if not current_user.is_gerente():
        return 'Acesso negado', 403

    periodo = request.args.get('periodo', 'mes')
    data_inicio_str = request.args.get('data_inicio')
    data_fim_str = request.args.get('data_fim')
    inicio, fim = get_periodo(periodo, data_inicio_str, data_fim_str)

    pagamentos = Pagamento.query.filter(
        Pagamento.criado_em >= inicio,
        Pagamento.criado_em <= fim,
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Data', 'Cliente', 'Tipo', 'Forma', 'Valor', 'Status'])
    for p in pagamentos:
        writer.writerow([
            p.criado_em.strftime('%d/%m/%Y'),
            p.cliente.nome,
            p.tipo,
            p.forma,
            f'R$ {p.valor:.2f}'.replace('.', ','),
            p.status,
        ])

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=arena_palhete_{inicio}_{fim}.csv'}
    )
