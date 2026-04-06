"""
web/app.py - Flask Web Dashboard
Web interface for monitoring and controlling the trading bot.
"""

from flask import Flask, render_template, jsonify, request
import MetaTrader5 as mt5
from datetime import datetime
from utils.helpers import get_account_info_summary, format_currency


def create_app(bot_instance):
    """Create and configure Flask app."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-here-change-in-production'
    
    # Store bot instance
    app.bot = bot_instance
    
    @app.route('/')
    def index():
        """Main dashboard page."""
        return render_template('dashboard.html')
    
    @app.route('/api/status')
    def api_status():
        """Get bot status and account info."""
        account_info = get_account_info_summary()
        
        return jsonify({
            'status': 'CHARLES\'S BOT' if app.bot.running else 'stopped',
            'bot_active': app.bot.bot_active,  # separate active status
            'auto_mode': app.bot.auto_mode,
            'account': account_info,
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/trades/open')
    def api_open_trades():
        """Get open positions."""
        if app.bot.trade_manager:
            positions = app.bot.trade_manager.get_open_positions_summary()
            return jsonify(positions)
        return jsonify([])
    
    @app.route('/api/trades/history')
    def api_trade_history():
        """Get trade history."""
        limit = request.args.get('limit', 50, type=int)
        trades = app.bot.db.get_all_trades(limit=limit)
        
        # Format for JSON
        for trade in trades:
            if trade.get('open_time'):
                trade['open_time'] = str(trade['open_time'])
            if trade.get('close_time'):
                trade['close_time'] = str(trade['close_time'])
        
        return jsonify(trades)
    
    @app.route('/api/performance')
    def api_performance():
        """Get performance summary."""
        days = request.args.get('days', 30, type=int)
        summary = app.bot.db.get_performance_summary(days=days)
        
        # Add current day P/L
        summary['today_pnl'] = app.bot.db.get_daily_pnl() or 0.0
        
        return jsonify(summary)
    
    @app.route('/api/toggle_mode', methods=['POST'])
    def api_toggle_mode():
        """Toggle between auto and manual mode."""
        app.bot.auto_mode = not app.bot.auto_mode
        
        return jsonify({
            'success': True,
            'auto_mode': app.bot.auto_mode,
            'message': f"Bot mode: {'AUTO' if app.bot.auto_mode else 'MANUAL'}"
        })
    
    @app.route('/api/toggle_bot', methods=['POST'])
    def api_toggle_bot():
        """Toggle bot active/inactive (Start/Stop)."""
        try:
            if app.bot.bot_active:
                app.bot.stop_bot()
                message = "Bot stopped (positions remain open)"
            else:
                app.bot.start_bot()
                message = "Bot started and active"
            
            return jsonify({
                'success': True,
                'bot_active': app.bot.bot_active,
                'message': message
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f"Error toggling bot: {str(e)}"
            }), 500
    
    @app.route('/api/close_position', methods=['POST'])
    def api_close_position():
        """Close a specific position."""
        try:
            data = request.get_json()
            ticket = data.get('ticket')
            
            if not ticket:
                return jsonify({'success': False, 'message': 'Ticket required'}), 400
            
            if app.bot.executor:
                success = app.bot.executor.close_position(ticket, "Manual close via dashboard")
                return jsonify({
                    'success': success,
                    'message': 'Position closed' if success else 'Failed to close position'
                })
            
            return jsonify({'success': False, 'message': 'Executor not initialized'}), 500
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f"Error: {str(e)}"
            }), 500
    
    @app.route('/api/close_all', methods=['POST'])
    def api_close_all():
        """Close all open positions."""
        try:
            if not app.bot.trade_manager:
                return jsonify({
                    'success': False,
                    'message': 'Trade manager not initialized'
                }), 500
            
            # Get current positions count
            positions = mt5.positions_get()
            if positions is None:
                positions_count = 0
            else:
                # Only count our bot's positions (magic number 234000)
                positions_count = sum(1 for p in positions if p.magic == 234000)
            
            if positions_count == 0:
                return jsonify({
                    'success': True,
                    'message': 'No open positions to close'
                })
            
            # Close all positions
            app.bot.trade_manager.close_all_trades("Manual close all via dashboard")
            
            return jsonify({
                'success': True,
                'message': f'Closed {positions_count} position(s) successfully'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f"Error closing positions: {str(e)}"
            }), 500
    
    @app.route('/api/stats/summary')
    def api_stats_summary():
        """Get overall statistics."""
        account = get_account_info_summary()
        performance = app.bot.db.get_performance_summary(days=30)
        
        # Get positions count (only our bot's positions)
        positions = mt5.positions_get()
        if positions is None:
            positions_count = 0
        else:
            positions_count = sum(1 for p in positions if p.magic == 234000)
        
        orders = mt5.orders_total()
        
        return jsonify({
            'account_balance': account.get('balance', 0),
            'account_equity': account.get('equity', 0),
            'daily_pnl': app.bot.db.get_daily_pnl() or 0,
            'open_positions': positions_count,
            'pending_orders': orders,
            'total_trades': performance.get('total_trades', 0),
            'win_rate': performance.get('win_rate', 0),
            'total_profit': performance.get('total_profit', 0)
        })
    @app.route('/api/floating_pnl')
    def api_floating_pnl():
        """Get total floating P/L."""
        try:
            if app.bot.trade_manager:
                floating_pnl = app.bot.trade_manager.get_total_floating_pnl()
                return jsonify({
                    'success': True,
                    'floating_pnl': floating_pnl
                })
            
            return jsonify({
                'success': False,
                'floating_pnl': 0.0,
                'message': 'Trade manager not initialized'
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'floating_pnl': 0.0,
                'error': str(e)
            }), 500
    
    @app.route('/api/close_profitable', methods=['POST'])
    def api_close_profitable():
        """Close only profitable positions."""
        try:
            if not app.bot.trade_manager:
                return jsonify({
                    'success': False,
                    'message': 'Trade manager not initialized'
                }), 500
            
            result = app.bot.trade_manager.close_profitable_positions("Manual close profitable via dashboard")
            
            if result['success']:
                message = f"Closed {result['closed_count']} profitable position(s) for ${result['total_profit']:.2f}. Skipped {result['skipped_count']} losing position(s)."
                return jsonify({
                    'success': True,
                    'message': message,
                    'closed_count': result['closed_count'],
                    'total_profit': result['total_profit'],
                    'skipped_count': result['skipped_count']
                })
            else:
                return jsonify(result), 500
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f"Error: {str(e)}"
            }), 500
    
    @app.route('/api/database/stats')
    def api_database_stats():
        """Get database statistics."""
        try:
            stats = app.bot.db.get_database_stats()
            return jsonify({
                'success': True,
                'stats': stats
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    @app.route('/api/database/cleanup', methods=['POST'])
    def api_database_cleanup():
        """Manual database cleanup."""
        try:
            data = request.get_json() or {}
            days = data.get('days', 90)
            
            result = app.bot.db.manual_cleanup(days=days)
            
            if result['success']:
                message = f"Cleaned {result['signals_deleted']} signals and {result['logs_deleted']} logs older than {days} days"
                return jsonify({
                    'success': True,
                    'message': message,
                    'stats': result
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result.get('error', 'Cleanup failed')
                }), 500
            
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f"Error: {str(e)}"
            }), 500
    return app