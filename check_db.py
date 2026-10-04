from app import app
from models import Order, OrderItem


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