"""
Script para inicializar o banco de dados e criar dados iniciais.
Execute: python seed.py
"""
from app import create_app
from app.models import db, Usuario, PlanoMensalista, Configuracao


def seed():
    app = create_app('development')
    with app.app_context():
        db.create_all()
        print("✅ Tabelas criadas.")

        # Usuários iniciais
        if not Usuario.query.filter_by(email='gerente@arenapalhete.com').first():
            gerente = Usuario(nome='Gerente', email='gerente@arenapalhete.com', perfil='gerente')
            gerente.set_senha('palhete2026')
            db.session.add(gerente)
            print("✅ Usuário gerente criado.")

        if not Usuario.query.filter_by(email='funcionario@arenapalhete.com').first():
            func = Usuario(nome='Funcionário', email='funcionario@arenapalhete.com', perfil='funcionario')
            func.set_senha('campo2026')
            db.session.add(func)
            print("✅ Usuário funcionário criado.")

        # Criação do usuário Admin adicional (solicitado)
        if not Usuario.query.filter_by(email='admin@palhete.com').first():
            admin = Usuario(nome='Gerente Palhete', email='admin@palhete.com', perfil='gerente')
            admin.set_senha('123456')
            db.session.add(admin)
            print("✅ Usuário admin criado.")

        # Planos mensalistas
        planos = [
            ('1h',   60,  600.0),
            ('1h30', 90,  700.0),
            ('2h',   120, 800.0),
        ]
        for nome, duracao, valor in planos:
            if not PlanoMensalista.query.filter_by(nome=nome).first():
                db.session.add(PlanoMensalista(nome=nome, duracao_minutos=duracao, valor_mensal=valor))
        print("✅ Planos mensalistas criados.")

        # Configurações padrão
        configs = {
            'hora_abertura': '8',
            'hora_fechamento': '23',
            'valor_avulso_hora': '150.0',
        }
        for chave, valor in configs.items():
            if not Configuracao.query.filter_by(chave=chave).first():
                db.session.add(Configuracao(chave=chave, valor=valor))
        print("✅ Configurações padrão criadas.")

        db.session.commit()
        print("\n🏟️  Arena Palhete pronto para uso!")
        print("   Gerente:     gerente@arenapalhete.com / palhete2026")
        print("   Funcionário: funcionario@arenapalhete.com / campo2026")
        print("   Admin:       admin@palhete.com / 123456")


if __name__ == '__main__':
    seed()