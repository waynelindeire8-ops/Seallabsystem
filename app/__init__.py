from flask import Flask, redirect
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    JWTManager(app)
    CORS(app)

    from app.database import init_db
    init_db()

    from app.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.samples import samples_bp
    from app.routes.catalog import catalog_bp
    from app.routes.sample_types import sample_types_bp
    from app.routes.clients import clients_bp
    from app.routes.patients import patients_bp
    from app.routes.reports import reports_bp
    from app.routes.users import users_bp
    from app.routes.settings import settings_bp
    from app.routes.test_groups import test_groups_bp
    from app.routes.test_categories import test_categories_bp
    from app.routes.lab_tests import lab_tests_bp
    from app.routes.test_parameters import test_parameters_bp
    from app.routes.specimens import specimens_bp
    from app.routes.machine_tests import machine_tests_bp
    from app.routes.suppliers import suppliers_bp
    from app.routes.items import items_bp
    from app.routes.sales import sales_bp
    from app.routes.invoices import invoices_bp
    from app.routes.deliveries import deliveries_bp
    from app.routes.quotations import quotations_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(samples_bp)
    app.register_blueprint(catalog_bp)
    app.register_blueprint(sample_types_bp)
    app.register_blueprint(clients_bp)
    app.register_blueprint(patients_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(test_groups_bp)
    app.register_blueprint(test_categories_bp)
    app.register_blueprint(lab_tests_bp)
    app.register_blueprint(test_parameters_bp)
    app.register_blueprint(specimens_bp)
    app.register_blueprint(machine_tests_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(sales_bp)
    app.register_blueprint(invoices_bp)
    app.register_blueprint(deliveries_bp)
    app.register_blueprint(quotations_bp)

    @app.route('/')
    def index():
        return redirect('/dashboard')

    return app
