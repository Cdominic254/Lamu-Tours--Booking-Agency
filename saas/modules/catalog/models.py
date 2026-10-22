from datetime import datetime

from saas.extensions import db


class Tour(db.Model):
    slug = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    duration = db.Column(db.String(80), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(100), nullable=False, default='Island experiences')
    itinerary = db.Column(db.Text, nullable=False, default='')
    inclusions = db.Column(db.Text, nullable=False, default='')
    exclusions = db.Column(db.Text, nullable=False, default='')
    pickup_point = db.Column(db.String(200), nullable=False, default='Lamu Town waterfront')
    min_group_size = db.Column(db.Integer, nullable=False, default=1)
    max_group_size = db.Column(db.Integer, nullable=False, default=12)
    image_url = db.Column(db.String(500), nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor_account.id'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'slug': self.slug,
            'name': self.name,
            'description': self.description,
            'duration': self.duration,
            'price': self.price,
            'category': self.category,
            'itinerary': self.itinerary.splitlines(),
            'inclusions': self.inclusions.splitlines(),
            'exclusions': self.exclusions.splitlines(),
            'pickup_point': self.pickup_point,
            'min_group_size': self.min_group_size,
            'max_group_size': self.max_group_size,
            'image_url': self.image_url,
        }


class TourSchedule(db.Model):
    __tablename__ = 'tour_schedule'
    __table_args__ = (db.UniqueConstraint('tour_slug', 'starts_at', name='uq_tour_schedule_start'),)

    id = db.Column(db.Integer, primary_key=True)
    tour_slug = db.Column(db.String(120), db.ForeignKey('tour.slug'), nullable=False, index=True)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    capacity = db.Column(db.Integer, nullable=False)
    booked_count = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'tour_slug': self.tour_slug,
            'starts_at': self.starts_at.isoformat(timespec='minutes'),
            'capacity': self.capacity,
            'booked_count': self.booked_count,
            'remaining': self.capacity - self.booked_count,
        }


class Property(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(160), unique=True, nullable=True)
    vendor_id = db.Column(db.Integer, db.ForeignKey('vendor_account.id'), nullable=True, index=True)
    owner_name = db.Column(db.String(100), nullable=False)
    owner_email = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    property_type = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(120), nullable=False)
    price_per_night = db.Column(db.Integer, nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    description = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'slug': self.slug,
            'name': self.name,
            'property_type': self.property_type,
            'location': self.location,
            'price_per_night': self.price_per_night,
            'guests': self.guests,
            'image_url': self.image_url,
            'description': self.description,
        }


class Destination(db.Model):
    slug = db.Column(db.String(120), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=True)
    search_location = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'slug': self.slug,
            'name': self.name,
            'description': self.description,
            'image_url': self.image_url,
            'search_location': self.search_location,
        }


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    reviewer_name = db.Column(db.String(100), nullable=False)
    reviewer_email = db.Column(db.String(120), nullable=False)
    place = db.Column(db.String(150), nullable=False)
    target_type = db.Column(db.String(20), nullable=True)
    target_id = db.Column(db.String(160), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'reviewer_name': self.reviewer_name,
            'place': self.place,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }
