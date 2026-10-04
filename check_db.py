from app import app
from models import Order, OrderItem, Product, ProductImage


with app.app_context():

    print("\n=== ЗАКАЗЫ ===")

    orders = Order.query.all()

    for order in orders:
        print(
            f"Заказ #{order.id} | "
            f"{order.customer_name} | "
            f"{order.total} ₽ | "
            f"{order.status}"
        )


    print("\n=== ТОВАРЫ В ЗАКАЗАХ ===")

    items = OrderItem.query.all()

    for item in items:
        print(
            f"Заказ #{item.order_id} | "
            f"Товар ID: {item.product_id} | "
            f"Количество: {item.quantity} | "
            f"Цена: {item.price} ₽"
        )


    print("\n=== ТОВАРЫ ===")

    products = Product.query.all()

    for product in products:
        print(
            f"Товар #{product.id} | "
            f"{product.name} | "
            f"Основное фото: {product.image}"
        )


    print("\n=== ФОТОГРАФИИ ТОВАРОВ ===")

    images = ProductImage.query.order_by(
        ProductImage.product_id,
        ProductImage.id
    ).all()

    if not images:
        print("Фотографий в ProductImage пока нет.")

    for image in images:
        print(
            f"Товар #{image.product_id} | "
            f"Фото ID: {image.id} | "
            f"Файл: {image.filename} | "
            f"Главное: {image.is_main}"
        )