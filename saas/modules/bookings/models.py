from datetime import datetime
import secrets

from saas.extensions import db


class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True, index=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('tour_schedule.id'), nullable=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(50), nullable=False)
    tour = db.Column(db.String(100), nullable=False)
    date = db.Column(db.String(20), nullable=False)
    time = db.Column(db.String(20), nullable=False)
    guests = db.Column(db.Integer, nullable=False)
    message = db.Column(db.Text, nullable=True)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    commission_rate = db.Column(db.Float, nullable=False, default=15.0)
    payment_status = db.Column(db.String(30), nullable=False, default='pending')
    payment_reference = db.Column(db.String(64), nullable=True, default=lambda: secrets.token_urlsafe(32))
    checkout_request_id = db.Column(db.String(100), nullable=True)
    merchant_request_id = db.Column(db.String(100), nullable=True)
    mpesa_receipt_number = db.Column(db.String(30), nullable=True, unique=True)
    refund_status = db.Column(db.String(30), nullable=False, default='none')
    status = db.Column(db.String(30), nullable=False, default='requested')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('uq_booking_payment_reference', 'payment_reference', unique=True),
        db.Index('uq_booking_checkout_request_id', 'checkout_request_id', unique=True),
        db.Index('uq_booking_mpesa_receipt_number', 'mpesa_receipt_number', unique=True),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'schedule_id': self.schedule_id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'tour': self.tour,
            'date': self.date,
            'time': self.time,
            'guests': self.guests,
            'message': self.message,
            'amount': self.amount,
            'commission_rate': self.commission_rate,
            'payment_status': self.payment_status,
            'mpesa_receipt_number': self.mpesa_receipt_number,
            'refund_status': self.refund_status,
            'status': self.status,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
        }


class BookingDispute(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='open')
    resolution = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'booking_id': self.booking_id,
            'reason': self.reason,
            'status': self.status,
            'resolution': self.resolution,
            'created_at': self.created_at.isoformat() + 'Z' if self.created_at else None,
            'resolved_at': self.resolved_at.isoformat() + 'Z' if self.resolved_at else None,
        }
