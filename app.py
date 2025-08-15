#!/usr/bin/env python3
"""
Central Bot API - Production Ready
Manages communication with all Sub Bots (friend devices)
"""
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import logging
import time

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Enable CORS for web browser access

# Security: API key for control operations
API_KEY = os.environ.get('API_KEY', 'twitter-bot-secret-2025')

# Storage
device_statuses = {}
command_queues = {}
recent_activities = {}

# ===== DEVICE COMMUNICATION ENDPOINTS =====

@app.route('/api/device/<device_id>/heartbeat', methods=['POST'])
def device_heartbeat(device_id):
    """Sub Bots send heartbeat every 30 seconds"""
    try:
        data = request.json or {}
        
        # Get last activity from recent activities
        last_activity = "Never"
        if device_id in recent_activities and recent_activities[device_id]:
            last_activity = recent_activities[device_id][0]['timestamp']
        
        device_statuses[device_id] = {
            'status': 'online',
            'last_seen': datetime.now().isoformat(),
            'uptime_hours': data.get('uptime_hours', 0),
            'cpu_usage': data.get('cpu_usage', 0),
            'actions_today': data.get('actions_today', {}),
            'next_scheduled': data.get('next_scheduled'),
            'content_version': data.get('content_version', 'unknown'),
            'twitter_logged_in': data.get('twitter_logged_in', False),
            'last_activity': last_activity
        }
        
        logger.info(f"💓 Heartbeat from {device_id}: {data.get('actions_today', {})}")
        return jsonify({'success': True, 'timestamp': datetime.now().isoformat()})
        
    except Exception as e:
        logger.error(f"Heartbeat error for {device_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/device/<device_id>/activity', methods=['POST'])
def log_device_activity(device_id):
    """Sub Bots report completed actions"""
    try:
        activity = request.json or {}
        
        if device_id not in recent_activities:
            recent_activities[device_id] = []
        
        activity_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': activity.get('action', 'unknown'),
            'success': activity.get('success', False),
            'details': activity.get('details', ''),
            'content_preview': activity.get('content_preview', '')[:100]
        }
        
        recent_activities[device_id].insert(0, activity_entry)
        recent_activities[device_id] = recent_activities[device_id][:50]  # Keep last 50
        
        # Update device status with last activity
        if device_id in device_statuses:
            device_statuses[device_id]['last_activity'] = activity_entry['timestamp']
        
        logger.info(f"📊 Activity from {device_id}: {activity.get('action')}")
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Activity logging error for {device_id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/device/<device_id>/commands', methods=['GET'])
def get_pending_commands(device_id):
    """Sub Bots check for commands every 10 seconds"""
    try:
        commands = command_queues.get(device_id, [])
        command_queues[device_id] = []  # Clear after sending
        
        if commands:
            logger.info(f"📤 Sending {len(commands)} commands to {device_id}")
        
        return jsonify({'commands': commands, 'timestamp': datetime.now().isoformat()})
        
    except Exception as e:
        logger.error(f"Command retrieval error for {device_id}: {e}")
        return jsonify({'commands': [], 'error': str(e)})

# ===== CONTROL ROOM ENDPOINTS =====

@app.route('/api/control/stop/<device_id>', methods=['POST'])
def stop_device(device_id):
    """Stop specific device"""
    try:
        add_command(device_id, 'stop_bot', {'reason': 'Manual stop from Control Room'})
        logger.info(f"🛑 Stop command sent to {device_id}")
        return jsonify({'success': True, 'message': f'Stop command sent to {device_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/control/restart/<device_id>', methods=['POST'])
def restart_device(device_id):
    """Restart specific device"""
    try:
        params = request.json or {}
        add_command(device_id, 'restart_bot', params)
        logger.info(f"🔄 Restart command sent to {device_id}")
        return jsonify({'success': True, 'message': f'Restart command sent to {device_id}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/control/emergency_stop_all', methods=['POST'])
def emergency_stop_all():
    """EMERGENCY: Stop ALL devices immediately"""
    try:
        stopped_devices = []
        
        for device_id in device_statuses.keys():
            add_command(device_id, 'emergency_stop', {'priority': 'critical'})
            stopped_devices.append(device_id)
        
        logger.warning(f"🚨 EMERGENCY STOP sent to {len(stopped_devices)} devices")
        return jsonify({
            'success': True, 
            'message': f'Emergency stop sent to {len(stopped_devices)} devices',
            'devices': stopped_devices
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ===== MONITORING ENDPOINTS =====

@app.route('/api/status/all', methods=['GET'])
def get_all_status():
    """Get complete fleet status"""
    try:
        cleanup_offline_devices()
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'devices': device_statuses,
            'recent_activities': recent_activities,
            'total_devices': len(device_statuses),
            'online_devices': len([d for d in device_statuses.values() if d['status'] == 'online'])
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/analytics', methods=['GET'])
def get_analytics():
    """Get detailed analytics for the fleet"""
    try:
        cleanup_offline_devices()
        
        devices = device_statuses
        total_devices = len(devices)
        online_devices = len([d for d in devices.values() if d.get('status') == 'online'])
        
        # Calculate total actions across all devices
        total_actions = 0
        total_tweets = 0
        total_replies = 0
        total_retweets = 0
        total_uptime = 0
        
        for device_data in devices.values():
            actions_today = device_data.get('actions_today', {})
            total_tweets += actions_today.get('tweets', 0)
            total_replies += actions_today.get('replies', 0)
            total_retweets += actions_today.get('retweets', 0)
            total_actions += sum(actions_today.values()) if isinstance(actions_today, dict) else 0
            total_uptime += device_data.get('uptime_hours', 0)
        
        # Calculate performance metrics
        avg_uptime = total_uptime / total_devices if total_devices > 0 else 0
        uptime_percentage = (online_devices / total_devices * 100) if total_devices > 0 else 0
        avg_actions_per_device = total_actions / total_devices if total_devices > 0 else 0
        
        # Get device details for analytics
        device_details = []
        for device_id, device_data in devices.items():
            actions_today = device_data.get('actions_today', {})
            total_device_actions = sum(actions_today.values()) if isinstance(actions_today, dict) else 0
            
            device_details.append({
                'id': device_id,
                'name': device_id.replace('bot_', ''),
                'status': device_data.get('status', 'unknown'),
                'uptime_hours': device_data.get('uptime_hours', 0),
                'actions_today': actions_today,
                'total_actions': total_device_actions,
                'last_activity': device_data.get('last_activity', 'Never'),
                'cpu_usage': device_data.get('cpu_usage', 0),
                'memory_usage': device_data.get('memory_usage', 0)
            })
        
        # Sort devices by total actions (performance)
        device_details.sort(key=lambda x: x['total_actions'], reverse=True)
        top_performers = device_details[:3] if len(device_details) >= 3 else device_details
        
        analytics_data = {
            'fleet_overview': {
                'total_devices': total_devices,
                'online_devices': online_devices,
                'offline_devices': total_devices - online_devices,
                'total_uptime_hours': total_uptime,
                'average_uptime_hours': avg_uptime
            },
            'action_breakdown': {
                'total_actions': total_actions,
                'tweets': total_tweets,
                'replies': total_replies,
                'retweets': total_retweets,
                'tweet_percentage': (total_tweets / total_actions * 100) if total_actions > 0 else 0,
                'reply_percentage': (total_replies / total_actions * 100) if total_actions > 0 else 0,
                'retweet_percentage': (total_retweets / total_actions * 100) if total_actions > 0 else 0
            },
            'device_details': device_details,
            'performance_metrics': {
                'avg_actions_per_device': avg_actions_per_device,
                'uptime_percentage': uptime_percentage,
                'action_efficiency': total_actions / total_uptime if total_uptime > 0 else 0,
                'device_health_score': (online_devices / total_devices * 100) if total_devices > 0 else 0
            },
            'top_performers': top_performers
        }
        
        return jsonify({
            'timestamp': datetime.now().isoformat(),
            'analytics': analytics_data
        })
    except Exception as e:
        logger.error(f"Analytics error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    """Basic info page"""
    return jsonify({
        'service': 'Central Bot API',
        'version': '1.0.0',
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'connected_devices': len(device_statuses),
        'endpoints': {
            'device_heartbeat': '/api/device/<id>/heartbeat [POST]',
            'device_commands': '/api/device/<id>/commands [GET]',
            'control_stop': '/api/control/stop/<id> [POST]',
            'emergency_stop': '/api/control/emergency_stop_all [POST]',
            'fleet_status': '/api/status/all [GET]',
            'analytics': '/api/status/analytics [GET]'
        }
    })

@app.route('/health')
def health_check():
    """Health check for Heroku"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

# ===== UTILITY FUNCTIONS =====

def add_command(device_id, action, params=None):
    """Add command to device queue"""
    if device_id not in command_queues:
        command_queues[device_id] = []
    
    command = {
        'command_id': f"{action}_{int(datetime.now().timestamp())}",
        'action': action,
        'parameters': params or {},
        'timestamp': datetime.now().isoformat()
    }
    
    command_queues[device_id].append(command)

def cleanup_offline_devices():
    """Remove devices offline > 10 minutes"""
    current_time = datetime.now()
    offline_devices = []
    
    for device_id, status in list(device_statuses.items()):
        last_seen = datetime.fromisoformat(status['last_seen'])
        minutes_offline = (current_time - last_seen).total_seconds() / 60
        
        if minutes_offline > 10:
            offline_devices.append(device_id)
            del device_statuses[device_id]

# ===== MAIN APPLICATION =====

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    
    logger.info("🎛️ Central Bot API starting...")
    logger.info(f"📡 Listening on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)
