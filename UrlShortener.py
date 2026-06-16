"""
URL Shortener - Like bit.ly
Create short URLs, track clicks, and manage links
Author: Python Learning Project
"""

import json
import os
import random
import string
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import sys
import argparse
import hashlib
import re

try:
    from flask import Flask, request, redirect, jsonify, render_template_string
except ImportError:
    print("❌ Please install Flask:")
    print("   pip install flask")
    sys.exit(1)

app = Flask(__name__)

class URLShortener:
    """URL Shortener engine with analytics"""
    
    def __init__(self, data_file: str = "urls.json"):
        self.data_file = data_file
        self.urls = {}
        self.clicks = {}
        self.load_data()
    
    def load_data(self):
        """Load URL data from JSON file"""
        if not os.path.exists(self.data_file):
            # Create default data
            self.urls = {}
            self.clicks = {}
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.urls = data.get('urls', {})
                self.clicks = data.get('clicks', {})
            
            print(f"✅ Loaded {len(self.urls)} shortened URLs")
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            self.urls = {}
            self.clicks = {}
    
    def save_data(self):
        """Save URL data to JSON file"""
        try:
            data = {
                'urls': self.urls,
                'clicks': self.clicks
            }
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Error saving data: {e}")
            return False
    
    def generate_short_code(self, length: int = 6) -> str:
        """Generate a random short code"""
        characters = string.ascii_letters + string.digits
        while True:
            code = ''.join(random.choice(characters) for _ in range(length))
            if code not in self.urls:
                return code
    
    def shorten_url(self, original_url: str, custom_code: str = None, 
                    expiry_days: int = None, password: str = None) -> Dict:
        """
        Shorten a URL
        
        Args:
            original_url: The long URL to shorten
            custom_code: Custom short code (optional)
            expiry_days: Number of days until link expires (optional)
            password: Password to access link (optional)
            
        Returns:
            Dictionary with short URL details
        """
        # Validate URL
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'http://' + original_url
        
        # Check if custom code is available
        if custom_code:
            if custom_code in self.urls:
                return {'error': 'Custom code already exists'}
            short_code = custom_code
        else:
            short_code = self.generate_short_code()
        
        # Save URL data
        self.urls[short_code] = {
            'original_url': original_url,
            'created_at': datetime.now().isoformat(),
            'clicks': 0,
            'expiry': (datetime.now() + timedelta(days=expiry_days)).isoformat() if expiry_days else None,
            'password': password,
            'custom': bool(custom_code)
        }
        
        self.clicks[short_code] = []
        self.save_data()
        
        return {
            'short_code': short_code,
            'short_url': f"http://localhost:5000/{short_code}",
            'original_url': original_url,
            'expiry': self.urls[short_code]['expiry'],
            'password_protected': bool(password)
        }
    
    def get_original_url(self, short_code: str, password: str = None) -> Dict:
        """
        Get original URL from short code
        
        Args:
            short_code: The short code
            password: Password to access (if required)
            
        Returns:
            Dictionary with URL info or error
        """
        if short_code not in self.urls:
            return {'error': 'URL not found'}
        
        url_data = self.urls[short_code]
        
        # Check expiry
        if url_data.get('expiry'):
            expiry_date = datetime.fromisoformat(url_data['expiry'])
            if datetime.now() > expiry_date:
                return {'error': 'URL has expired'}
        
        # Check password
        if url_data.get('password'):
            if not password or password != url_data['password']:
                return {'error': 'Password required', 'password_required': True}
        
        # Log click
        self.log_click(short_code)
        
        return {
            'original_url': url_data['original_url'],
            'success': True
        }
    
    def log_click(self, short_code: str):
        """Log a click for analytics"""
        if short_code in self.urls:
            self.urls[short_code]['clicks'] += 1
            
            if short_code not in self.clicks:
                self.clicks[short_code] = []
            
            self.clicks[short_code].append({
                'timestamp': datetime.now().isoformat(),
                'user_agent': request.headers.get('User-Agent') if hasattr(request, 'headers') else None,
                'ip': request.remote_addr if hasattr(request, 'remote_addr') else None
            })
            
            self.save_data()
    
    def get_stats(self, short_code: str) -> Dict:
        """Get statistics for a short URL"""
        if short_code not in self.urls:
            return {'error': 'URL not found'}
        
        url_data = self.urls[short_code]
        click_data = self.clicks.get(short_code, [])
        
        return {
            'short_code': short_code,
            'original_url': url_data['original_url'],
            'created_at': url_data['created_at'],
            'total_clicks': url_data['clicks'],
            'recent_clicks': click_data[-10:] if click_data else [],  # Last 10 clicks
            'expiry': url_data.get('expiry'),
            'password_protected': bool(url_data.get('password'))
        }
    
    def delete_url(self, short_code: str) -> bool:
        """Delete a shortened URL"""
        if short_code in self.urls:
            del self.urls[short_code]
            if short_code in self.clicks:
                del self.clicks[short_code]
            self.save_data()
            return True
        return False
    
    def search_urls(self, query: str) -> List[Dict]:
        """Search for URLs by original URL"""
        results = []
        query_lower = query.lower()
        for code, data in self.urls.items():
            if query_lower in data['original_url'].lower():
                results.append({
                    'short_code': code,
                    'original_url': data['original_url'],
                    'clicks': data['clicks'],
                    'created_at': data['created_at']
                })
        return results
    
    def get_all_urls(self) -> List[Dict]:
        """Get all shortened URLs"""
        return [{
            'short_code': code,
            'original_url': data['original_url'],
            'clicks': data['clicks'],
            'created_at': data['created_at'],
            'expiry': data.get('expiry'),
            'password_protected': bool(data.get('password'))
        } for code, data in self.urls.items()]

# Flask Routes
shortener = URLShortener()

@app.route('/')
def home():
    """Home page with URL shortener form"""
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URL Shortener</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 600px;
            width: 90%;
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
        }
        .input-group {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        input[type="text"] {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            padding: 12px 24px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
        }
        .result {
            background: #f5f5f5;
            padding: 15px;
            border-radius: 8px;
            margin-top: 20px;
            display: none;
        }
        .result.show {
            display: block;
        }
        .short-url {
            color: #667eea;
            word-break: break-all;
        }
        .short-url a {
            color: #667eea;
            text-decoration: none;
        }
        .short-url a:hover {
            text-decoration: underline;
        }
        .options {
            margin: 20px 0;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 8px;
        }
        .options label {
            display: block;
            margin: 8px 0;
            color: #555;
            font-size: 14px;
        }
        .options input[type="text"],
        .options input[type="number"],
        .options input[type="password"] {
            width: 100%;
            padding: 8px 12px;
            border: 1px solid #ddd;
            border-radius: 4px;
            margin-top: 4px;
        }
        .stats-link {
            text-align: center;
            margin-top: 15px;
        }
        .stats-link a {
            color: #667eea;
            text-decoration: none;
            font-size: 14px;
        }
        .stats-link a:hover {
            text-decoration: underline;
        }
        .error {
            color: #e74c3c;
            margin-top: 10px;
            display: none;
        }
        .error.show {
            display: block;
        }
        .success {
            color: #27ae60;
            margin-top: 10px;
            display: none;
        }
        .success.show {
            display: block;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 URL Shortener</h1>
        <p class="subtitle">Make your links short and memorable</p>
        
        <div class="input-group">
            <input type="text" id="urlInput" placeholder="Enter URL to shorten...">
            <button onclick="shortenUrl()">Shorten</button>
        </div>
        
        <div class="options">
            <label>
                Custom alias (optional):
                <input type="text" id="customCode" placeholder="e.g., mylink">
            </label>
            <label>
                Expiry (days, optional):
                <input type="number" id="expiryDays" placeholder="e.g., 7" min="1">
            </label>
            <label>
                Password protect (optional):
                <input type="password" id="password" placeholder="Set a password">
            </label>
        </div>
        
        <div id="result" class="result">
            <p>✅ Short URL created!</p>
            <p class="short-url">🔗 <a id="shortUrlLink" href="#" target="_blank"></a></p>
            <p style="font-size: 14px; color: #666; margin-top: 5px;">Original: <span id="originalUrlDisplay"></span></p>
            <p id="expiryDisplay" style="font-size: 14px; color: #666; margin-top: 5px;"></p>
        </div>
        
        <div id="error" class="error"></div>
        <div id="success" class="success"></div>
        
        <div class="stats-link">
            <a href="/stats">📊 View All Shortened URLs</a>
        </div>
    </div>
    
    <script>
        function shortenUrl() {
            const url = document.getElementById('urlInput').value;
            const customCode = document.getElementById('customCode').value;
            const expiryDays = document.getElementById('expiryDays').value;
            const password = document.getElementById('password').value;
            
            if (!url) {
                showError('Please enter a URL');
                return;
            }
            
            const data = {
                url: url,
                custom_code: customCode,
                expiry_days: expiryDays ? parseInt(expiryDays) : null,
                password: password || null
            };
            
            fetch('/shorten', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(data)
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    showResult(data);
                }
            })
            .catch(error => {
                showError('Error shortening URL');
                console.error(error);
            });
        }
        
        function showResult(data) {
            document.getElementById('error').classList.remove('show');
            document.getElementById('success').classList.remove('show');
            
            const result = document.getElementById('result');
            result.classList.add('show');
            
            document.getElementById('shortUrlLink').textContent = data.short_url;
            document.getElementById('shortUrlLink').href = data.short_url;
            document.getElementById('originalUrlDisplay').textContent = data.original_url;
            
            if (data.expiry) {
                document.getElementById('expiryDisplay').textContent = `⏰ Expires: ${new Date(data.expiry).toLocaleDateString()}`;
            } else {
                document.getElementById('expiryDisplay').textContent = '⏰ Never expires';
            }
            
            // Show password protection notice
            if (data.password_protected) {
                document.getElementById('expiryDisplay').textContent += ' 🔒 Password protected';
            }
        }
        
        function showError(message) {
            document.getElementById('result').classList.remove('show');
            document.getElementById('success').classList.remove('show');
            const error = document.getElementById('error');
            error.textContent = '❌ ' + message;
            error.classList.add('show');
        }
        
        function showSuccess(message) {
            document.getElementById('result').classList.remove('show');
            document.getElementById('error').classList.remove('show');
            const success = document.getElementById('success');
            success.textContent = '✅ ' + message;
            success.classList.add('show');
        }
        
        // Enter key to submit
        document.getElementById('urlInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                shortenUrl();
            }
        });
    </script>
</body>
</html>
    ''')

@app.route('/shorten', methods=['POST'])
def shorten():
    """API endpoint to shorten URL"""
    data = request.get_json()
    
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400
    
    original_url = data['url']
    custom_code = data.get('custom_code')
    expiry_days = data.get('expiry_days')
    password = data.get('password')
    
    result = shortener.shorten_url(original_url, custom_code, expiry_days, password)
    
    if 'error' in result:
        return jsonify({'error': result['error']}), 400
    
    return jsonify(result)

@app.route('/<short_code>')
def redirect_to_url(short_code):
    """Redirect short URL to original"""
    # Check if password is required
    if short_code in shortener.urls:
        if shortener.urls[short_code].get('password'):
            password = request.args.get('password')
            result = shortener.get_original_url(short_code, password)
            
            if result.get('password_required'):
                return render_template_string('''
<!DOCTYPE html>
<html>
<head>
    <title>Password Required</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 100px auto; padding: 20px; }
        input { padding: 10px; width: 100%; margin: 10px 0; }
        button { padding: 10px 20px; background: #667eea; color: white; border: none; cursor: pointer; }
    </style>
</head>
<body>
    <h2>🔒 Password Required</h2>
    <p>This link is password protected. Please enter the password:</p>
    <form method="GET">
        <input type="password" name="password" placeholder="Enter password">
        <button type="submit">Access Link</button>
    </form>
</body>
</html>
                ''')
    
    result = shortener.get_original_url(short_code)
    
    if 'error' in result:
        return render_template_string('''
<!DOCTYPE html>
<html>
<head><title>Error</title></head>
<body>
    <h2>❌ {{ error }}</h2>
    <p><a href="/">Go back to home</a></p>
</body>
</html>
        ''', error=result['error'])
    
    return redirect(result['original_url'])

@app.route('/stats')
def stats():
    """View all shortened URLs"""
    urls = shortener.get_all_urls()
    
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>URL Statistics</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            background: #f5f5f5;
            padding: 40px 20px;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 16px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        h1 { color: #333; margin-bottom: 20px; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th {
            background: #667eea;
            color: white;
        }
        tr:hover {
            background: #f9f9f9;
        }
        .back-link {
            display: inline-block;
            margin-top: 20px;
            color: #667eea;
            text-decoration: none;
        }
        .back-link:hover {
            text-decoration: underline;
        }
        .clickable {
            color: #667eea;
            cursor: pointer;
            text-decoration: none;
        }
        .clickable:hover {
            text-decoration: underline;
        }
        .badge {
            display: inline-block;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 12px;
        }
        .badge-password {
            background: #f39c12;
            color: white;
        }
        .badge-expired {
            background: #e74c3c;
            color: white;
        }
        .badge-active {
            background: #27ae60;
            color: white;
        }
        .delete-btn {
            background: #e74c3c;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
        }
        .delete-btn:hover {
            background: #c0392b;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 URL Statistics</h1>
        <p>Total URLs: {{ urls|length }}</p>
        
        <table>
            <thead>
                <tr>
                    <th>Short Code</th>
                    <th>Original URL</th>
                    <th>Clicks</th>
                    <th>Created</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for url in urls %}
                <tr>
                    <td><a href="/{{ url.short_code }}" class="clickable" target="_blank">{{ url.short_code }}</a></td>
                    <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <a href="{{ url.original_url }}" target="_blank">{{ url.original_url[:50] }}{% if url.original_url|length > 50 %}...{% endif %}</a>
                    </td>
                    <td>{{ url.clicks }}</td>
                    <td>{{ url.created_at[:10] }}</td>
                    <td>
                        {% if url.expiry %}
                            {% if url.expiry < now %}
                                <span class="badge badge-expired">Expired</span>
                            {% else %}
                                <span class="badge badge-active">Active</span>
                            {% endif %}
                        {% else %}
                            <span class="badge badge-active">Active</span>
                        {% endif %}
                        {% if url.password_protected %}
                            <span class="badge badge-password">🔒</span>
                        {% endif %}
                    </td>
                    <td>
                        <form action="/delete/{{ url.short_code }}" method="POST" style="display: inline;">
                            <button type="submit" class="delete-btn" onclick="return confirm('Delete this URL?')">Delete</button>
                        </form>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <a href="/" class="back-link">← Back to Home</a>
    </div>
</body>
</html>
    ''', urls=urls, now=datetime.now().isoformat())

@app.route('/delete/<short_code>', methods=['POST'])
def delete_url(short_code):
    """Delete a shortened URL"""
    if shortener.delete_url(short_code):
        return redirect('/stats')
    return "URL not found", 404

@app.route('/stats/<short_code>')
def url_stats(short_code):
    """Get detailed stats for a specific URL"""
    stats = shortener.get_stats(short_code)
    
    if 'error' in stats:
        return jsonify({'error': stats['error']}), 404
    
    return jsonify(stats)

@app.route('/api/urls')
def api_urls():
    """API endpoint to get all URLs"""
    return jsonify(shortener.get_all_urls())

def run_cli():
    """Command line interface for the URL shortener"""
    shortener = URLShortener()
    
    print("\n" + "="*60)
    print("🔗 URL SHORTENER - CLI Mode")
    print("="*60)
    
    while True:
        print("\n📌 MENU")
        print("="*40)
        print("1. Shorten URL")
        print("2. Get Stats")
        print("3. List All URLs")
        print("4. Search URLs")
        print("5. Delete URL")
        print("6. Start Web Server")
        print("7. Exit")
        print("="*40)
        
        choice = input("\n👉 Enter your choice (1-7): ").strip()
        
        if choice == '1':
            url = input("Enter URL to shorten: ").strip()
            custom = input("Custom code (optional): ").strip() or None
            expiry = input("Expiry days (optional): ").strip()
            expiry = int(expiry) if expiry else None
            password = input("Password protect (optional): ").strip() or None
            
            result = shortener.shorten_url(url, custom, expiry, password)
            
            if 'error' in result:
                print(f"❌ Error: {result['error']}")
            else:
                print(f"\n✅ Short URL created!")
                print(f"   Short URL: {result['short_url']}")
                print(f"   Original: {result['original_url']}")
                if result.get('expiry'):
                    print(f"   Expires: {result['expiry'][:10]}")
                if result.get('password_protected'):
                    print("   🔒 Password protected")
        
        elif choice == '2':
            code = input("Enter short code: ").strip()
            stats = shortener.get_stats(code)
            
            if 'error' in stats:
                print(f"❌ {stats['error']}")
            else:
                print(f"\n📊 Stats for: {code}")
                print(f"   Original URL: {stats['original_url']}")
                print(f"   Total Clicks: {stats['total_clicks']}")
                print(f"   Created: {stats['created_at'][:10]}")
                if stats.get('expiry'):
                    print(f"   Expires: {stats['expiry'][:10]}")
                if stats.get('password_protected'):
                    print("   🔒 Password protected")
        
        elif choice == '3':
            urls = shortener.get_all_urls()
            if not urls:
                print("📭 No URLs found")
            else:
                print(f"\n📋 All URLs ({len(urls)}):")
                print("-"*60)
                for url in urls:
                    print(f"  {url['short_code']} → {url['original_url'][:50]}...")
                    print(f"    Clicks: {url['clicks']} | Created: {url['created_at'][:10]}")
                    if url.get('expiry'):
                        print(f"    Expires: {url['expiry'][:10]}")
                    if url.get('password_protected'):
                        print("    🔒 Password protected")
                    print()
        
        elif choice == '4':
            query = input("Search query: ").strip()
            results = shortener.search_urls(query)
            if not results:
                print("📭 No results found")
            else:
                print(f"\n📋 Search results ({len(results)}):")
                for result in results:
                    print(f"  {result['short_code']} → {result['original_url']}")
                    print(f"    Clicks: {result['clicks']}")
        
        elif choice == '5':
            code = input("Enter short code to delete: ").strip()
            confirm = input(f"Delete {code}? (y/n): ").lower()
            if confirm == 'y':
                if shortener.delete_url(code):
                    print("✅ URL deleted")
                else:
                    print("❌ URL not found")
        
        elif choice == '6':
            print("\n🚀 Starting web server...")
            print("🌐 Open http://localhost:5000 in your browser")
            print("Press Ctrl+C to stop")
            app.run(debug=True, host='0.0.0.0', port=5000)
        
        elif choice == '7':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")

def main():
    parser = argparse.ArgumentParser(description='URL Shortener')
    parser.add_argument('--cli', action='store_true', help='Run in CLI mode')
    parser.add_argument('--port', type=int, default=5000, help='Port for web server')
    parser.add_argument('--host', default='0.0.0.0', help='Host for web server')
    
    args = parser.parse_args()
    
    if args.cli:
        run_cli()
    else:
        print("\n" + "="*60)
        print("🔗 URL SHORTENER - Web Server")
        print("="*60)
        print(f"\n🚀 Starting server at http://localhost:{args.port}")
        print("📝 Access CLI mode with: python url_shortener.py --cli")
        print("Press Ctrl+C to stop\n")
        app.run(debug=True, host=args.host, port=args.port)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)