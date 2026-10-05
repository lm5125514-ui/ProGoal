from database import db


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(150), nullable=False)

    category = db.Column(db.String(100), nullable=False)

    brand = db.Column(db.String(100), nullable=False)

    price = db.Column(db.Integer, nullable=False)

    description = db.Column(db.Text, nullable=False)

    image = db.Column(db.String(255), nullable=True)

    images = db.relationship(
        "ProductImage",
        backref="product",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Product {self.name}>"

class ProductImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    filename = db.Column(
        db.String(255),
        nullable=False
    )

    is_main = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    customer_name = db.Column(db.String(150), nullable=False)
    customer_phone = db.Column(db.String(50), nullable=False)
    customer_address = db.Column(db.String(255), nullable=False)

    total = db.Column(db.Integer, nullable=False)

    status = db.Column(
        db.String(50),
        nullable=False,
        default="Новый"
    )

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("order.id"),
        nullable=False
    )

    product_id = db.Column(
        db.Integer,
        db.ForeignKey("product.id"),
        nullable=False
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    price = db.Column(
        db.Integer,
        nullable=False
    )

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(
        db.String(100),
        nullable=False
    )

    email = db.Column(
        db.String(150),
        unique=True,
        nullable=False
    )

    phone = db.Column(
        db.String(50),
        nullable=True
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now(),
        nullable=False
    )


class UserOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    order_id = db.Column(
        db.Integer,
        db.ForeignKey("order.id"),
        nullable=False,
        unique=True
    )

    user = db.relationship(
        "User",
        backref=db.backref(
            "user_orders",
            lazy=True,
            cascade="all, delete-orphan"
        )
    )

    order = db.relationship(
        "Order",
        backref=db.backref(
            "user_order_link",
            uselist=False
        )
    )
