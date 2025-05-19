from flask import Blueprint, request, jsonify
from models import db, WebHook
from uuid import uuid4
from flask_jwt_extended import jwt_required, get_current_user
from datetime import datetime, timedelta

webhook_bp = Blueprint('webhook', __name__)

def utc7now():
    return datetime.utcnow() + timedelta(hours=7)

@webhook_bp.route('/add', methods=['POST'])
@jwt_required()
def add_webhook():
    current_user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    key = data.get('key')
    typeweb = data.get('typeweb', 'Telegram')
    if not user_id or not key:
        return jsonify({"error": "user_id và key là bắt buộc"}), 400
    webhook = WebHook(
        id=uuid4(),
        user_id=current_user.id,
        key=key,
        typeweb=typeweb
    )
    db.session.add(webhook)
    db.session.commit()
    return jsonify({
        "id": str(webhook.id),
        "user_id": current_user.id,
        "key": webhook.key,
        "typeweb": webhook.typeweb,
        "time_created": webhook.time_created.isoformat(),
        "is_deleted": webhook.is_deleted,
        "deleted_at": webhook.deleted_at.isoformat() if webhook.deleted_at else None
    }), 201

@webhook_bp.route('/<string:webhook_id>', methods=['DELETE'])
@jwt_required()
def delete_webhook(webhook_id):
    current_user = get_current_user()
    webhook = WebHook.query.filter_by(id=webhook_id, user_id=current_user.id, is_deleted=False).first()
    if not webhook:
        return jsonify({"error": "Webhook không tồn tại hoặc đã bị xoá"}), 404
    webhook.is_deleted = True
    webhook.deleted_at = utc7now()
    db.session.commit()
    return jsonify({"message": "Xoá webhook thành công"}), 200

@webhook_bp.route('/<string:webhook_id>', methods=['PUT'])
@jwt_required()
def update_webhook(webhook_id):
    current_user = get_current_user()
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400
    webhook = WebHook.query.filter_by(id=webhook_id, user_id=current_user.id, is_deleted=False).first()
    if not webhook:
        return jsonify({"error": "Webhook không tồn tại hoặc đã bị xoá"}), 404
    key = data.get('key')
    typeweb = data.get('typeweb')
    if key:
        webhook.key = key
    if typeweb:
        webhook.typeweb = typeweb
    db.session.commit()
    return jsonify({
        "id": str(webhook.id),
        "user_id": webhook.user_id,
        "key": webhook.key,
        "typeweb": webhook.typeweb,
        "time_created": webhook.time_created.isoformat(),
        "is_deleted": webhook.is_deleted,
        "deleted_at": webhook.deleted_at.isoformat() if webhook.deleted_at else None
    }), 200 