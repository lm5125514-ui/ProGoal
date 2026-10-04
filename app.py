import os

from dotenv import load_dotenv

load_dotenv()

from flask import (
    Flask,
    render_template,
    request,
    session,
    redirect,
    url_for
)

from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
import uuid
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database import db
from models import Product, ProductImage, Order, OrderItem, Admin


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

app.config["UPLOAD_FOLDER"] = os.path.join(
    app.static_folder,
    "images",
    "products"
)

ALLOWED_IMAGE_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp"
}

app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

def allowed_image(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_IMAGE_EXTENSIONS
    )

# Безопасные настройки cookie сессии
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False


# CSRF-защита
csrf = CSRFProtect(app)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[]
)

# Подключаем базу данных
db.init_app(app)

with app.app_context():
    db.create_all()


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

    selected_category = request.args.get("category")
    selected_brand = request.args.get("brand")

    query = Product.query

    if selected_category:
        query = query.filter_by(
            category=selected_category
        )

    if selected_brand:
        query = query.filter_by(
            brand=selected_brand
        )

    products = query.order_by(
        Product.id.desc()
    ).all()

    brands = [
        row[0]
        for row in db.session.query(
            Product.brand
        ).distinct().order_by(
            Product.brand
        ).all()
    ]

    return render_template(
        "catalog.html",
        products=products,
        selected_category=selected_category,
        selected_brand=selected_brand,
        brands=brands
    )


# =========================
# СТРАНИЦА ТОВАРА
# =========================

@app.route("/product/<int:product_id>")
def product(product_id):

    product = Product.query.get_or_404(product_id)

    images = ProductImage.query.filter_by(
        product_id=product.id
    ).order_by(
        ProductImage.is_main.desc(),
        ProductImage.id.asc()
    ).all()

    return render_template(
        "product.html",
        product=product,
        images=images
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

@app.route("/track-order", methods=["GET", "POST"])
def track_order():

    order = None
    error = None

    if request.method == "POST":

        order_id = request.form.get("order_id", "").strip()
        phone = request.form.get("phone", "").strip()

        if not order_id or not phone:
            error = "Введите номер заказа и телефон."

        else:
            try:
                order_id = int(order_id)

                order = Order.query.filter_by(
                    id=order_id,
                    customer_phone=phone
                ).first()

                if not order:
                    error = "Заказ не найден. Проверьте номер заказа и телефон."

            except ValueError:
                error = "Номер заказа должен быть числом."

    return render_template(
        "track_order.html",
        order=order,
        error=error
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
@limiter.limit("5 per minute", methods=["POST"])
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
# АДМИН — ТОВАРЫ
# =========================

@app.route("/admin/products")
def admin_products():

    # Проверяем авторизацию администратора
    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    products = Product.query.order_by(
        Product.id.desc()
    ).all()

    return render_template(
        "admin_products.html",
        products=products
    )

@app.route("/admin/products/add", methods=["GET", "POST"])
def admin_add_product():

    # Проверяем авторизацию администратора
    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        brand = request.form.get("brand", "").strip()
        price = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()

        # Получаем ВСЕ загруженные изображения
        images = request.files.getlist("images")

        # Проверяем обязательные поля
        if not name or not category or not brand or not price or not description:
            return render_template(
                "admin_product_add.html",
                error="Заполните все обязательные поля.",
                form=request.form
            )

        # Убираем пустые файлы
        valid_images = [
            image_file
            for image_file in images
            if image_file and image_file.filename
        ]

        # Проверяем расширения всех изображений
        for image_file in valid_images:

            if not allowed_image(image_file.filename):
                return render_template(
                    "admin_product_add.html",
                    error=(
                        "Разрешены только изображения "
                        "JPG, JPEG, PNG и WEBP."
                    ),
                    form=request.form
                )

        # Проверяем цену
        try:
            price = int(price)

            if price <= 0:
                raise ValueError

        except ValueError:
            return render_template(
                "admin_product_add.html",
                error="Цена должна быть положительным целым числом.",
                form=request.form
            )

        # Создаём товар
        product = Product(
            name=name,
            category=category,
            brand=brand,
            price=price,
            description=description,
            image=None
        )

        db.session.add(product)
        db.session.flush()

        # Сохраняем изображения
        for index, image_file in enumerate(valid_images):

            original_name = secure_filename(
                image_file.filename
            )

            extension = original_name.rsplit(
                ".",
                1
            )[1].lower()

            filename = (
                f"product_{uuid.uuid4().hex}.{extension}"
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            image_file.save(image_path)

            # Первое изображение становится главным
            if index == 0:
                product.image = (
                    f"images/products/{filename}"
                )

            product_image = ProductImage(
                product_id=product.id,
                filename=filename,
                is_main=(index == 0)
            )

            db.session.add(product_image)

        db.session.commit()

        return redirect(
            url_for("admin_products")
        )

    return render_template(
        "admin_product_add.html",
        error=None,
        form={}
    )

@app.route(
    "/admin/products/<int:product_id>/edit",
    methods=["GET", "POST"]
)
def admin_edit_product(product_id):

    # Проверяем авторизацию администратора
    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    # Находим товар
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        category = request.form.get("category", "").strip()
        brand = request.form.get("brand", "").strip()
        price = request.form.get("price", "").strip()
        description = request.form.get("description", "").strip()

        # Получаем все загруженные изображения
        images = request.files.getlist("images")

        # Проверяем обязательные поля
        if not name or not category or not brand or not price or not description:
            return render_template(
                "admin_product_edit.html",
                product=product,
                error="Заполните все обязательные поля."
            )

        # Убираем пустые файлы
        valid_images = [
            image_file
            for image_file in images
            if image_file and image_file.filename
        ]

        # Проверяем расширения всех изображений
        for image_file in valid_images:

            if not allowed_image(image_file.filename):
                return render_template(
                    "admin_product_edit.html",
                    product=product,
                    error=(
                        "Разрешены только изображения "
                        "JPG, JPEG, PNG и WEBP."
                    )
                )

        # Проверяем цену
        try:
            price = int(price)

            if price <= 0:
                raise ValueError

        except ValueError:
            return render_template(
                "admin_product_edit.html",
                product=product,
                error="Цена должна быть положительным целым числом."
            )

        # Обновляем основные данные товара
        product.name = name
        product.category = category
        product.brand = brand
        product.price = price
        product.description = description

        # Проверяем, есть ли уже изображения у товара
        existing_images = ProductImage.query.filter_by(
            product_id=product.id
        ).all()

        # Сохраняем новые изображения
        for index, image_file in enumerate(valid_images):

            original_name = secure_filename(
                image_file.filename
            )

            # Дополнительная защита от файла без расширения
            if "." not in original_name:
                continue

            extension = original_name.rsplit(
                ".",
                1
            )[1].lower()

            filename = (
                f"product_{uuid.uuid4().hex}.{extension}"
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                filename
            )

            image_file.save(image_path)

            # Первое новое фото становится главным
            if index == 0:

                for existing_image in existing_images:
                    existing_image.is_main = False

                product.image = (
                    f"images/products/{filename}"
                )

                is_main = True

            else:
                is_main = False

            product_image = ProductImage(
                product_id=product.id,
                filename=filename,
                is_main=is_main
            )

            db.session.add(product_image)

        db.session.commit()

        return redirect(
            url_for("admin_products")
        )

    return render_template(
        "admin_product_edit.html",
        product=product,
        error=None
    )

@app.route(
    "/admin/products/<int:product_id>/delete",
    methods=["POST"]
)
def admin_delete_product(product_id):

    # Проверяем авторизацию администратора
    if "admin_id" not in session:
        return redirect(
            url_for("admin_login")
        )

    # Находим товар
    product = Product.query.get_or_404(product_id)

    # Запоминаем файлы всех фотографий товара
    image_filenames = [
        image.filename
        for image in product.images
    ]

    # Удаляем товар из базы данных
    db.session.delete(product)
    db.session.commit()

    # Удаляем файлы фотографий с диска
    for filename in image_filenames:

        image_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        if os.path.exists(image_path):
            os.remove(image_path)

    return redirect(
        url_for("admin_products")
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