from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default='funcionario')
    ativo = db.Column(db.Boolean, default=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    def is_gerente(self):
        return self.perfil == 'gerente'


class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='avulso')  
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    reservas = db.relationship('Reserva', backref='cliente', lazy=True)
    contratos = db.relationship('ContratoMensalista', backref='cliente', lazy=True)
    pagamentos = db.relationship('Pagamento', backref='cliente', lazy=True)

    def total_reservas_mes(self):
        hoje = date.today()
        return Reserva.query.filter(
            Reserva.cliente_id == self.id,
            db.extract('month', Reserva.data) == hoje.month,
            db.extract('year', Reserva.data) == hoje.year
        ).count()


class PlanoMensalista(db.Model):
    __tablename__ = 'planos_mensalista'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(20), nullable=False)        
    duracao_minutos = db.Column(db.Integer, nullable=False) 
    valor_mensal = db.Column(db.Float, nullable=False)

    contratos = db.relationship('ContratoMensalista', backref='plano', lazy=True)


class ContratoMensalista(db.Model):
    __tablename__ = 'contratos_mensalista'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    plano_id = db.Column(db.Integer, db.ForeignKey('planos_mensalista.id'), nullable=False)
    
    frequencia = db.Column(db.String(20), nullable=False, default='mensalista') 
    dia_semana = db.Column(db.Integer, nullable=False)  
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False) 
    data_inicio = db.Column(db.Date, nullable=False, default=date.today)
    data_fim = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(20), default='ativo')  

    pagamentos = db.relationship('Pagamento', backref='contrato', lazy=True)

    def mensalidade_mes(self, mes, ano):
        return Pagamento.query.filter_by(
            contrato_id=self.id,
            tipo='mensalidade',
            mes_referencia=f'{ano}-{mes:02d}'
        ).first()


class Reserva(db.Model):
    __tablename__ = 'reservas'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    data = db.Column(db.Date, nullable=False)
    hora_inicio = db.Column(db.Time, nullable=False)
    hora_fim = db.Column(db.Time, nullable=False)
    tipo = db.Column(db.String(20), nullable=False, default='avulso')  
    status = db.Column(db.String(20), default='confirmada')  
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    pagamento = db.relationship('Pagamento', backref='reserva', uselist=False, lazy=True)

    def duracao_minutos(self):
        ini = self.hora_inicio.hour * 60 + self.hora_inicio.minute
        fim = self.hora_fim.hour * 60 + self.hora_fim.minute
        minutos = fim - ini
        # Se virar a meia-noite (ex: 23h as 01h), corrige o valor negativo
        if minutos < 0:
            minutos += 24 * 60
        return minutos


class Pagamento(db.Model):
    __tablename__ = 'pagamentos'
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clientes.id'), nullable=False)
    reserva_id = db.Column(db.Integer, db.ForeignKey('reservas.id'), nullable=True)
    contrato_id = db.Column(db.Integer, db.ForeignKey('contratos_mensalista.id'), nullable=True)
    tipo = db.Column(db.String(20), nullable=False)         
    valor = db.Column(db.Float, nullable=False)
    forma = db.Column(db.String(20), nullable=False)        
    status = db.Column(db.String(20), default='pago')       
    mes_referencia = db.Column(db.String(7), nullable=True) 
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)


class Configuracao(db.Model):
    __tablename__ = 'configuracoes'
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(50), unique=True, nullable=False)
    valor = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.String(200), nullable=True)

    @staticmethod
    def get(chave, default=None):
        conf = Configuracao.query.filter_by(chave=chave).first()
        return conf.valor if conf else default

    @staticmethod
    def set(chave, valor, descricao=None):
        conf = Configuracao.query.filter_by(chave=chave).first()
        if conf:
            conf.valor = str(valor)
            if descricao:
                conf.descricao = descricao
        else:
            conf = Configuracao(chave=chave, valor=str(valor), descricao=descricao)
            db.session.add(conf)
        db.session.commit()