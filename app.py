import time
import random
import hashlib
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from flask import Flask, render_template, request, redirect, url_for, flash, session

# Flask app setup
app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Simplified B+ Tree Node
class BPlusTreeNode:
    def __init__(self, leaf=False):
        self.keys = []
        self.children = []
        self.leaf = leaf
        self.values = [] if leaf else None

class BPlusTree:
    def __init__(self, order=3):
        self.root = BPlusTreeNode(leaf=True)
        self.order = order

    def insert(self, key, value):
        root = self.root
        if len(root.keys) >= self.order:
            new_root = BPlusTreeNode()
            new_root.children.append(self.root)
            self.split_child(new_root, 0)
            self.root = new_root
        self.insert_non_full(self.root, key, value)

    def insert_non_full(self, node, key, value):
        if node.leaf:
            i = len(node.keys) - 1
            node.keys.append(0)
            node.values.append(None)
            while i >= 0 and node.keys[i] > key:
                node.keys[i + 1] = node.keys[i]
                node.values[i + 1] = node.values[i]
                i -= 1
            node.keys[i + 1] = key
            node.values[i + 1] = value
        else:
            i = len(node.keys) - 1
            while i >= 0 and node.keys[i] > key:
                i -= 1
            i += 1
            child = node.children[i]
            if len(child.keys) >= self.order:
                self.split_child(node, i)
                if key > node.keys[i]:
                    i += 1
            self.insert_non_full(node.children[i], key, value)

    def split_child(self, parent, index):
        order = self.order
        child = parent.children[index]
        new_node = BPlusTreeNode(leaf=child.leaf)
        
        mid = order // 2
        if child.leaf:
            parent.keys.insert(index, child.keys[mid])
            new_node.keys = child.keys[mid:]
            child.keys = child.keys[:mid]
            new_node.values = child.values[mid:]
            child.values = child.values[:mid]
        else:
            parent.keys.insert(index, child.keys[mid])
            new_node.keys = child.keys[mid + 1:]
            child.keys = child.keys[:mid]
            new_node.children = child.children[mid + 1:]
            child.children = child.children[:mid + 1]
        
        parent.children.insert(index + 1, new_node)

    def search(self, key):
        return self._search(self.root, key)

    def _search(self, node, key):
        i = 0
        while i < len(node.keys) and key > node.keys[i]:
            i += 1
        if node.leaf:
            for j in range(len(node.keys)):
                if node.keys[j] == key:
                    return node.values[j]
            return None
        return self._search(node.children[i], key)

    def range_search(self, start_key, end_key):
        results = []
        self._range_search(self.root, start_key, end_key, results)
        return results

    def _range_search(self, node, start_key, end_key, results):
        if node.leaf:
            for i in range(len(node.keys)):
                if start_key <= node.keys[i] <= end_key:
                    results.append((node.keys[i], node.values[i]))
            return
        
        i = 0
        while i < len(node.keys) and start_key > node.keys[i]:
            i += 1
        
        j = i
        while j < len(node.children):
            if j > 0 and j <= len(node.keys) and node.keys[j-1] > end_key:
                break
            self._range_search(node.children[j], start_key, end_key, results)
            j += 1

class HashIndex:
    def __init__(self):
        self.index = {}

    def insert(self, key, value):
        self.index[key] = value

    def search(self, key):
        return self.index.get(key)

    def range_search(self, start_key, end_key):
        results = []
        for key, value in self.index.items():
            if start_key <= key <= end_key:
                results.append((key, value))
        return sorted(results, key=lambda x: x[0])

# MongoDB Connection Setup
class Database:
    def __init__(self):
        try:
            self.client = MongoClient("mongodb://localhost:27017/")
            self.db = self.client["GameManagementDB"]
            self.games = self.db["games"]
            self.customers = self.db["customers"]
            self.admins = self.db["admins"]
            self._init_admin()
        except ConnectionFailure:
            print("Failed to connect to MongoDB. Ensure MongoDB is running.")
            exit(1)

    def _init_admin(self):
        admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
        if not self.admins.find_one({"username": "admin"}):
            self.admins.insert_one({"username": "admin", "password": admin_hash})

# User Authentication
class UserManager:
    def __init__(self, db):
        self.db = db

    def customer_signup(self, username, password):
        if self.db.customers.find_one({"username": username}) or self.db.admins.find_one({"username": username}):
            return False
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        self.db.customers.insert_one({"username": username, "password": hashed_password})
        return True

    def customer_login(self, username, password):
        customer = self.db.customers.find_one({"username": username})
        if customer:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            return customer["password"] == hashed_password
        return False

    def admin_login(self, username, password):
        admin = self.db.admins.find_one({"username": "admin"})
        if admin:
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            return admin["password"] == hashed_password
        return False

# Game Management System with Hybrid Indexing
class GameManagementSystem:
    def __init__(self):
        self.db = Database()
        self.user_manager = UserManager(self.db)
        self.bplus_tree = BPlusTree(order=3)
        self.hash_index = HashIndex()
        self.query_stats = {'equality': 0, 'range': 0}
        self.current_index = 'bplus'
        self.load_games()

    def load_games(self):
        for game in self.db.games.find():
            game_id = game["game_id"]
            title = game["title"]
            self.bplus_tree.insert(game_id, title)
            self.hash_index.insert(game_id, title)

    def add_game(self, game_id, title):
        if not session.get('is_admin'):
            return False
        if self.db.games.find_one({"game_id": game_id}):
            return False
        self.db.games.insert_one({"game_id": game_id, "title": title})
        self.bplus_tree.insert(game_id, title)
        self.hash_index.insert(game_id, title)
        return True

    def update_query_stats(self, query_type):
        if query_type == 'equality':
            self.query_stats['equality'] += 1
        elif query_type == 'range':
            self.query_stats['range'] += 1

        total_queries = self.query_stats['equality'] + self.query_stats['range']
        if total_queries > 0:
            equality_ratio = self.query_stats['equality'] / total_queries
            if equality_ratio > 0.9:
                self.current_index = 'hash'
            else:
                self.current_index = 'bplus'

    def find_game(self, game_id, query_type='equality'):
        self.update_query_stats(query_type)

        start_time = time.time()
        bplus_result = self.bplus_tree.search(game_id)
        bplus_time = time.time() - start_time

        start_time = time.time()
        hash_result = self.hash_index.search(game_id)
        hash_time = time.time() - start_time

        result = hash_result if self.current_index == 'hash' else bplus_result
        return result, bplus_time, hash_time

    def range_search(self, start_id, end_id):
        self.update_query_stats('range')

        start_time = time.time()
        bplus_results = self.bplus_tree.range_search(start_id, end_id)
        bplus_time = time.time() - start_time

        start_time = time.time()
        hash_results = self.hash_index.range_search(start_id, end_id)
        hash_time = time.time() - start_time

        return bplus_results, bplus_time, hash_results, hash_time

    def update_game(self, game_id, new_title):
        if not session.get('is_admin'):
            return False
        result = self.db.games.update_one(
            {"game_id": game_id},
            {"$set": {"title": new_title}}
        )
        if result.modified_count > 0:
            self.bplus_tree.insert(game_id, new_title)
            self.hash_index.insert(game_id, new_title)
        return result.modified_count > 0

    def delete_game(self, game_id):
        if not session.get('is_admin'):
            return False
        result = self.db.games.delete_one({"game_id": game_id})
        if result.deleted_count > 0:
            self.bplus_tree = BPlusTree(order=3)
            self.hash_index = HashIndex()
            self.load_games()
        return result.deleted_count > 0

    def benchmark_workload(self, num_queries, query_type):
        if not session.get('is_admin'):
            return None, None, None

        start_time = time.time()
        for _ in range(num_queries):
            if query_type == 'equality':
                game_id = random.randint(1, 100)
                self.bplus_tree.search(game_id)
            elif query_type == 'range':
                start_id = random.randint(1, 50)
                end_id = start_id + random.randint(1, 10)
                self.bplus_tree.range_search(start_id, end_id)
            elif query_type == 'mixed':
                if random.random() < 0.5:
                    game_id = random.randint(1, 100)
                    self.bplus_tree.search(game_id)
                    self.query_stats['equality'] += 1
                else:
                    start_id = random.randint(1, 50)
                    end_id = start_id + random.randint(1, 10)
                    self.bplus_tree.range_search(start_id, end_id)
                    self.query_stats['range'] += 1
        bplus_time = time.time() - start_time

        start_time = time.time()
        for _ in range(num_queries):
            if query_type == 'equality':
                game_id = random.randint(1, 100)
                self.hash_index.search(game_id)
            elif query_type == 'range':
                start_id = random.randint(1, 50)
                end_id = start_id + random.randint(1, 10)
                self.hash_index.range_search(start_id, end_id)
            elif query_type == 'mixed':
                if random.random() < 0.5:
                    game_id = random.randint(1, 100)
                    self.hash_index.search(game_id)
                else:
                    start_id = random.randint(1, 50)
                    end_id = start_id + random.randint(1, 10)
                    self.hash_index.range_search(start_id, end_id)
        hash_time = time.time() - start_time

        if bplus_time < hash_time:
            self.current_index = 'bplus'
        else:
            self.current_index = 'hash'

        return bplus_time, hash_time, self.current_index

    def customer_signup(self, username, password):
        return self.user_manager.customer_signup(username, password)

    def customer_login(self, username, password):
        if self.user_manager.customer_login(username, password):
            session['current_user'] = username
            session['is_admin'] = False
            return True
        return False

    def admin_login(self, username, password):
        if self.user_manager.admin_login(username, password):
            session['current_user'] = username
            session['is_admin'] = True
            return True
        return False

game_system = GameManagementSystem()

# Flask Routes
@app.route('/')
def main_menu():
    return render_template('main_menu.html')

@app.route('/customer')
def customer_menu():
    return render_template('customer_login.html')

@app.route('/customer/signup')
def customer_signup_page():
    return render_template('customer_signup.html')

@app.route('/customer/signup', methods=['POST'])
def customer_signup():
    username = request.form['username']
    password = request.form['password']
    if game_system.customer_signup(username, password):
        flash("Sign up successful! Please log in.", "success")
        return redirect(url_for('customer_menu'))
    else:
        flash("Username already exists. Try a different one.", "error")
        return redirect(url_for('customer_signup_page'))

@app.route('/customer/login', methods=['POST'])
def customer_login():
    username = request.form['username']
    password = request.form['password']
    if game_system.customer_login(username, password):
        flash("Login successful!", "success")
        return redirect(url_for('customer_operations'))
    else:
        flash("Invalid username or password.", "error")
        return redirect(url_for('customer_menu'))

@app.route('/customer/operations')
def customer_operations():
    if not session.get('current_user') or session.get('is_admin'):
        flash("Please log in as a customer.", "error")
        return redirect(url_for('customer_menu'))
    return render_template('customer_ops.html')

@app.route('/customer/search', methods=['POST'])
def customer_search():
    if not session.get('current_user') or session.get('is_admin'):
        flash("Please log in as a customer.", "error")
        return redirect(url_for('customer_menu'))
    game_id = request.form['game_id']
    try:
        game_id = int(game_id)
        result, bplus_time, hash_time = game_system.find_game(game_id)
        if result:
            flash(f"Game {game_id}: {result}", "success")
            flash(f"B+ Tree Search Time: {bplus_time:.6f} seconds", "info")
            flash(f"Hash Index Search Time: {hash_time:.6f} seconds", "info")
        else:
            flash(f"Game {game_id} not found.", "error")
    except ValueError:
        flash("Invalid game ID. Please enter a number.", "error")
    return redirect(url_for('customer_operations'))

@app.route('/customer/range_search', methods=['POST'])
def customer_range_search():
    if not session.get('current_user') or session.get('is_admin'):
        flash("Please log in as a customer.", "error")
        return redirect(url_for('customer_menu'))
    start_id = request.form['start_id']
    end_id = request.form['end_id']
    try:
        start_id = int(start_id)
        end_id = int(end_id)
        bplus_results, bplus_time, hash_results, hash_time = game_system.range_search(start_id, end_id)
        if bplus_results:
            flash("B+ Tree Range Search Results:", "success")
            for game_id, title in bplus_results:
                flash(f"Game {game_id}: {title}", "success")
            flash(f"B+ Tree Range Search Time: {bplus_time:.6f} seconds", "info")
        else:
            flash("No games found in range (B+ Tree).", "error")

        if hash_results:
            flash("Hash Index Range Search Results:", "success")
            for game_id, title in hash_results:
                flash(f"Game {game_id}: {title}", "success")
            flash(f"Hash Index Range Search Time: {hash_time:.6f} seconds", "info")
        else:
            flash("No games found in range (Hash Index).", "error")
    except ValueError:
        flash("Invalid range. Please enter numbers.", "error")
    return redirect(url_for('customer_operations'))

@app.route('/admin')
def admin_menu():
    return render_template('admin_login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    username = request.form['username']
    password = request.form['password']
    if game_system.admin_login(username, password):
        flash("Login successful!", "success")
        return redirect(url_for('admin_operations'))
    else:
        flash("Invalid username or password.", "error")
        return redirect(url_for('admin_menu'))

@app.route('/admin/operations')
def admin_operations():
    if not session.get('current_user') or not session.get('is_admin'):
        flash("Please log in as an admin.", "error")
        return redirect(url_for('admin_menu'))
    return render_template('admin_ops.html')

@app.route('/admin/add', methods=['POST'])
def admin_add_game():
    if not session.get('is_admin'):
        flash("Unauthorized access.", "error")
        return redirect(url_for('main_menu'))
    game_id = request.form['game_id']
    title = request.form['title']
    try:
        game_id = int(game_id)
        if game_system.add_game(game_id, title):
            flash("Game added successfully!", "success")
        else:
            flash("Failed to add game. Game ID may already exist.", "error")
    except ValueError:
        flash("Invalid game ID. Please enter a number.", "error")
    return redirect(url_for('admin_operations'))

@app.route('/admin/search', methods=['POST'])
def admin_search():
    if not session.get('is_admin'):
        flash("Unauthorized access.", "error")
        return redirect(url_for('main_menu'))
    game_id = request.form['game_id']
    try:
        game_id = int(game_id)
        result, bplus_time, hash_time = game_system.find_game(game_id)
        if result:
            flash(f"Game {game_id}: {result}", "success")
            flash(f"B+ Tree Search Time: {bplus_time:.6f} seconds", "info")
            flash(f"Hash Index Search Time: {hash_time:.6f} seconds", "info")
        else:
            flash(f"Game {game_id} not found.", "error")
    except ValueError:
        flash("Invalid game ID. Please enter a number.", "error")
    return redirect(url_for('admin_operations'))

@app.route('/admin/range_search', methods=['POST'])
def admin_range_search():
    if not session.get('is_admin'):
        flash("Unauthorized access.", "error")
        return redirect(url_for('main_menu'))
    start_id = request.form['start_id']
    end_id = request.form['end_id']
    try:
        start_id = int(start_id)
        end_id = int(end_id)
        bplus_results, bplus_time, hash_results, hash_time = game_system.range_search(start_id, end_id)
        if bplus_results:
            flash("B+ Tree Range Search Results:", "success")
            for game_id, title in bplus_results:
                flash(f"Game {game_id}: {title}", "success")
            flash(f"B+ Tree Range Search Time: {bplus_time:.6f} seconds", "info")
        else:
            flash("No games found in range (B+ Tree).", "error")

        if hash_results:
            flash("Hash Index Range Search Results:", "success")
            for game_id, title in hash_results:
                flash(f"Game {game_id}: {title}", "success")
            flash(f"Hash Index Range Search Time: {hash_time:.6f} seconds", "info")
        else:
            flash("No games found in range (Hash Index).", "error")
    except ValueError:
        flash("Invalid range. Please enter numbers.", "error")
    return redirect(url_for('admin_operations'))

@app.route('/admin/update', methods=['POST'])
def admin_update_game():
    if not session.get('is_admin'):
        flash("Unauthorized access.", "error")
        return redirect(url_for('main_menu'))
    game_id = request.form['game_id']
    new_title = request.form['new_title']
    try:
        game_id = int(game_id)
        if game_system.update_game(game_id, new_title):
            flash("Game updated successfully!", "success")
        else:
            flash("Failed to update game. Game not found.", "error")
    except ValueError:
        flash("Invalid game ID. Please enter a number.", "error")
    return redirect(url_for('admin_operations'))

@app.route('/admin/delete', methods=['POST'])
def admin_delete_game():
    if not session.get('is_admin'):
        flash("Unauthorized access.", "error")
        return redirect(url_for('main_menu'))
    game_id = request.form['game_id']
    try:
        game_id = int(game_id)
        if game_system.delete_game(game_id):
            flash("Game deleted successfully!", "success")
        else:
            flash("Failed to delete game. Game not found.", "error")
    except ValueError:
        flash("Invalid game ID. Please enter a number.", "error")
    return redirect(url_for('admin_operations'))

@app.route('/admin/benchmark', methods=['POST'])
def admin_benchmark():
    if not session.get('is_admin'):
        flash("Unauthorized access.", "error")
        return redirect(url_for('main_menu'))
    num_queries = request.form['num_queries']
    query_type = request.form['query_type']
    try:
        num_queries = int(num_queries)
        if query_type not in ['equality', 'range', 'mixed']:
            flash("Invalid query type. Use 'equality', 'range', or 'mixed'.", "error")
            return redirect(url_for('admin_operations'))
        bplus_time, hash_time, current_index = game_system.benchmark_workload(num_queries, query_type)
        if bplus_time is not None:
            flash(f"{query_type.capitalize()} Queries ({num_queries}):", "success")
            flash(f"B+ Tree Time: {bplus_time:.4f} seconds", "info")
            flash(f"Hash Index Time: {hash_time:.4f} seconds", "info")
            flash(f"Current Index Used: {current_index.capitalize()}", "info")
        else:
            flash("Benchmarking is only available for admins.", "error")
    except ValueError:
        flash("Invalid number of queries. Please enter a number.", "error")
    return redirect(url_for('admin_operations'))

@app.route('/logout')
def logout():
    session.pop('current_user', None)
    session.pop('is_admin', None)
    flash("Logged out successfully.", "success")
    return redirect(url_for('main_menu'))

# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)