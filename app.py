import os

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for
)

from werkzeug.security import check_password_hash
from flask_wtf import CSRFProtect

from database import db
from models import Product, Order, OrderItem, Admin


app = Flask(__name__)


# =========================
# НАСТРОЙКИ
# =========================

secret_key = os.environ.get("SECRET_KEY")

if not secret_key:
    raise RuntimeError(
        "SECRET_KEY не задан. "
        "Укажите SECRET_KEY в переменных окружения."
    )

app.secret_key = secret_key

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///progoal.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# Безопасные настройки cookie сессии
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False


# CSRF-защита
csrf = CSRFProtect(app)


# Подключаем базу данных
db.init_app(app)


# =========================
# ГЛАВНАЯ
# =========================

@app.route("/")
def home():
    return render_template("index.html")


# =========================
# КАТАЛОГ
# =========================

@app.route("/contacts")
def contacts():
    return render_template("contacts.html")

@app.route("/catalog")
def catalog():

    category = request.args.get("category")

    if category:
        products = Product.query.filter_by(
            category=category
        ).all()
    else:
        products = Product.query.all()

    return render_template(
        "catalog.html",
        products=products,
        selected_category=category
    )


# =========================
# СТРАНИЦА ТОВАРА
# =========================

@app.route("/product/<int:product_id>")
def product(product_id):

    product = Product.query.get_or_404(product_id)

    return render_template(
        "product.html",
        product=product
    )


# =========================
# ДОБАВЛЕНИЕ В КОРЗИНУ
# =========================

@app.post("/cart/add/<int:product_id>")
def add_to_cart(product_id):

    product = Product.query.get_or_404(product_id)

    cart = session.get("cart", {})

    product_id_str = str(product.id)

    current_quantity = cart.get(
        product_id_str,
        0
    )

    # Максимум 10 одинаковых товаров
    if current_quantity >= 10:
        return redirect(
            request.referrer or url_for("catalog")
        )

    cart[product_id_str] = current_quantity + 1

    session["cart"] = cart

    return redirect(
        request.referrer or url_for("catalog")
    )


# =========================
# КОРЗИНА
# =========================

@app.route("/cart")
def cart():

    cart = session.get("cart", {})

    products = []
    total = 0

    for product_id, quantity in cart.items():

        product = Product.query.get(
            int(product_id)
        )

        if product:

            item_total = product.price * quantity

            total += item_total

            products.append({
                "product": product,
                "quantity": quantity,
                "item_total": item_total
            })

    return render_template(
        "cart.html",
        products=products,
        total=total
    )


# =========================
# ОФОРМЛЕНИЕ ЗАКАЗА
# =========================

@app.route("/checkout", methods=["GET", "POST"])
def checkout():

    cart = session.get("cart", {})

    # Если корзина пустая
    if not cart:
        return redirect(
            url_for("cart")
        )

    products = []
    total = 0

    # Получаем товары корзины
    for product_id, quantity in cart.items():

        product = Product.query.get(
            int(product_id)
        )

        if product:

            item_total = product.price * quantity

            total += item_total

            products.append({
                "product": product,
                "quantity": quantity,
                "item_total": item_total
            })

    # Если пользователь отправил форму
    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        address = request.form.get(
            "address",
            ""
        ).strip()

        error = None

        # Проверка обязательных полей
        if not name or not phone or not address:

            error = "Заполните все поля"

        # Проверка имени
        elif len(name) < 2 or len(name) > 100:

            error = (
                "Имя должно содержать "
                "от 2 до 100 символов"
            )

        # Проверка телефона
        elif len(phone) < 5 or len(phone) > 30:

            error = (
                "Введите корректный "
                "номер телефона"
            )

        # Проверка адреса
        elif len(address) < 5 or len(address) > 255:

            error = (
                "Адрес должен содержать "
                "от 5 до 255 символов"
            )

        # Если есть ошибка
        if error:

            return render_template(
                "checkout.html",
                products=products,
                total=total,
                error=error
            )

        # Создаём заказ
        order = Order(
            customer_name=name,
            customer_phone=phone,
            customer_address=address,
            total=total,
            status="Новый"
        )

        db.session.add(order)

        # Получаем ID заказа
        db.session.flush()

        # Сохраняем товары заказа
        for product_id, quantity in cart.items():

            product = Product.query.get(
                int(product_id)
            )

            if product:

                order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    price=product.price
                )

                db.session.add(order_item)

        # Сохраняем заказ в БД
        db.session.commit()

        # Запоминаем последний созданный заказ
        session["last_order_id"] = order.id

        # Очищаем корзину
        session["cart"] = {}

        return redirect(
            url_for(
                "order_success",
                order_id=order.id
            )
        )

    return render_template(
        "checkout.html",
        products=products,
        total=total
    )


# =========================
# УСПЕШНЫЙ ЗАКАЗ
# =========================

@app.route("/order-success/<int:order_id>")
def order_success(order_id):

    # Проверяем, что этот заказ был создан
    # из текущей пользовательской сессии
    if session.get("last_order_id") != order_id:
        return redirect(
            url_for("home")
        )

    order = Order.query.get_or_404(
        order_id
    )

    return render_template(
        "order_success.html",
        order=order
    )


# =========================
# ОБНОВЛЕНИЕ КОРЗИНЫ
# =========================

@app.post("/cart/update/<int:product_id>/<action>")
def update_cart(product_id, action):

    cart = session.get(
        "cart",
        {}
    )

    product_id_str = str(product_id)

    if product_id_str in cart:

        # Увеличение
        if action == "increase":

            if cart[product_id_str] < 10:
                cart[product_id_str] += 1

        # Уменьшение
        elif action == "decrease":

            cart[product_id_str] -= 1

            if cart[product_id_str] <= 0:

                del cart[product_id_str]

    session["cart"] = cart

    return redirect(
        url_for("cart")
    )


# =========================
# AJAX ОБНОВЛЕНИЕ КОРЗИНЫ
# =========================

@app.post("/cart/update-ajax/<int:product_id>/<action>")
def update_cart_ajax(product_id, action):

    cart = session.get(
        "cart",
        {}
    )

    product_id_str = str(product_id)

    # Товара нет в корзине
    if product_id_str not in cart:

        return {
            "success": False,
            "message": "Товар не найден"
        }

    # Увеличение количества
    if action == "increase":

        if cart[product_id_str] >= 10:

            return {
                "success": False,
                "message": (
                    "Максимальное количество "
                    "товара — 10"
                )
            }

        cart[product_id_str] += 1

    # Уменьшение количества
    elif action == "decrease":

        cart[product_id_str] -= 1

        if cart[product_id_str] <= 0:

            del cart[product_id_str]

    else:

        return {
            "success": False,
            "message": "Неизвестное действие"
        }

    session["cart"] = cart

    quantity = cart.get(
        product_id_str,
        0
    )

    product = Product.query.get(
        product_id
    )

    if not product:

        return {
            "success": False,
            "message": "Товар не найден"
        }

    # Пересчитываем общую сумму
    total = 0

    for cart_product_id, cart_quantity in cart.items():

        cart_product = Product.query.get(
            int(cart_product_id)
        )

        if cart_product:

            total += (
                cart_product.price
                * cart_quantity
            )

    return {
        "success": True,
        "quantity": quantity,
        "item_total": (
            product.price * quantity
        ),
        "total": total
    }


# =========================
# УДАЛЕНИЕ ИЗ КОРЗИНЫ
# =========================

@app.post("/cart/remove/<int:product_id>")
def remove_from_cart(product_id):

    cart = session.get(
        "cart",
        {}
    )

    product_id_str = str(product_id)

    if product_id_str in cart:

        del cart[product_id_str]

    session["cart"] = cart

    return redirect(
        url_for("cart")
    )


# =========================
# АДМИН — ВХОД
# =========================

@app.route(
    "/admin/login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username"
        )

        password = request.form.get(
            "password"
        )

        admin = Admin.query.filter_by(
            username=username
        ).first()

        # Проверяем логин и пароль
        if admin and check_password_hash(
            admin.password,
            password
        ):

            session["admin_id"] = admin.id

            return redirect(
                url_for("admin_orders")
            )

        return render_template(
            "admin_login.html",
            error="Неверный логин или пароль"
        )

    return render_template(
        "admin_login.html"
    )


# =========================
# АДМИН — ВЫХОД
# =========================

@app.route("/admin/logout")
def admin_logout():

    session.pop(
        "admin_id",
        None
    )

    return redirect(
        url_for("admin_login")
    )


# =========================
# АДМИН — ЗАКАЗЫ
# =========================

@app.route("/admin/orders")
def admin_orders():

    # Проверяем авторизацию администратора
    if "admin_id" not in session:

        return redirect(
            url_for("admin_login")
        )

    orders = Order.query.order_by(
        Order.id.desc()
    ).all()

    return render_template(
        "admin_orders.html",
        orders=orders
    )

@app.route("/admin/orders/<int:order_id>")
def admin_order_detail(order_id):
    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    order = Order.query.get_or_404(order_id)

    items = OrderItem.query.filter_by(
        order_id=order.id
    ).all()

    products = []

    for item in items:
        product = Product.query.get(item.product_id)

        if product:
            products.append({
                "product": product,
                "quantity": item.quantity,
                "price": item.price,
                "item_total": item.price * item.quantity
            })

    return render_template(
        "admin_order_detail.html",
        order=order,
        products=products
    )

@app.post("/admin/orders/<int:order_id>/status")
def update_order_status(order_id):

    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    order = Order.query.get_or_404(order_id)

    new_status = request.form.get("status")

    allowed_statuses = [
        "Новый",
        "В обработке",
        "Собран",
        "Отправлен",
        "Выполнен"
    ]

    if new_status in allowed_statuses:
        order.status = new_status
        db.session.commit()

    return redirect(
        url_for(
            "admin_order_detail",
            order_id=order.id
        )
    )


# =========================
# ОШИБКА 404
# =========================

@app.errorhandler(404)
def page_not_found(error):
    return render_template(
        "404.html"
    ), 404

# =========================
# ОШИБКА 500
# =========================

@app.errorhandler(500)
def internal_server_error(error):
    db.session.rollback()

    return render_template(
        "500.html"
    ), 500

# =========================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =========================

if __name__ == "__main__":

    with app.app_context():

        db.create_all()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=os.environ.get("FLASK_DEBUG") == "1"
    )