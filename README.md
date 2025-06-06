# ADBMS-Hybrid-Indexing
1. Introduction
1.1. Project Title
Game Management System with Hybrid Indexing

1.2. Purpose
The Game Management System is a web-based application designed to manage a collection of games using a MongoDB database. The primary goal is to implement a hybrid indexing mechanism combining a B+ Tree and a Hash Index to optimize query performance for equality and range searches. The system supports user authentication, game management functionalities for admins (add, update, delete games), and performance benchmarking to compare the two indexing methods.

1.3. Objectives
•	Implement a hybrid indexing system using a B+ Tree for range searches and a Hash Index for equality searches.
•	Develop a Flask-based web application with user authentication for customers and admins.
•	Provide functionalities for searching games (equality and range searches) and managing games (admin only).
•	Optimize performance by dynamically switching between indexes based on query patterns and benchmark results.
•	Document the development process, challenges, fixes, and performance analysis with visual evidence.

3. Methodology
2.1. System Design
The system is designed as a Flask web application with a MongoDB backend. It uses two indexing structures:
•	B+ Tree: For efficient range searches and competitive equality searches.
•	Hash Index: For fast equality searches using a Python dictionary.
•	Adaptive Mechanism: Switches between indexes based on query type ratios and benchmark performance.

2.2. Technologies Used
•	Flask: Web framework for building the application.
•	MongoDB: Database for storing games, customers, and admin data.
•	Python: Backend logic, including B+ Tree and Hash Index implementations.
•	HTML/CSS: Front-end templates for user interfaces.

2.3. Data Storage
•	Database: GameManagementDB
•	Collections:
o	games: Stores 1000 games with game_id (1 to 1000) and title (e.g., Game_1 to Game_1000).
o	customers: Stores customer credentials (username, password).
o	admins: Stores admin credentials (default: username="admin", password="admin123").

2.4. Development Process
•	Phase 1: Set up Flask, MongoDB, and initial data (1000 games).
•	Phase 2: Implement B+ Tree and Hash Index classes with insert, search, and range_search methods.
•	Phase 3: Develop user authentication and Flask routes for customer and admin operations.
•	Phase 4: Add adaptive indexing logic to switch between B+ Tree and Hash Index.
•	Phase 5: Debug and fix issues (e.g., B+ Tree range search, equality search, index selection).
•	Phase 6: Document the project with results and screenshots.

3. Implementation
3.1. Code Structure
•	BPlusTree Class:
o	Methods: insert, search, range_search.
o	Order: 3 (maximum 3 keys per node).
o	Leaf nodes store (key, value) pairs (game_id, title).
•	HashIndex Class:
o	Uses a Python dictionary for O(1) equality searches.
o	range_search scans the entire dictionary (O(n) complexity).
•	GameManagementSystem Class:
o	Manages database interactions, indexing, and query handling.
o	Key methods: load_games, find_game, range_search, add_game, update_game, delete_game, benchmark_workload.
•	Flask Routes:
o	Customer routes: /customer/signup, /customer/login, /customer/search, /customer/range_search.
o	Admin routes: /admin/login, /admin/add, /admin/search, /admin/range_search, /admin/update, /admin/delete, /admin/benchmark.

3.2. Key Features
•	User Authentication: Customers can sign up and log in; admins use default credentials.
•	Game Management: Admins can add, update, and delete games.
•	Search Operations:
o	Equality search: Find a game by game_id.
o	Range search: Find games within a game_id range.
•	Adaptive Indexing: Switches between B+ Tree and Hash Index based on query patterns and performance.
•	Benchmarking: Measures performance of both indexes for equality, range, and mixed workloads.

3.3. Challenges and Solutions
•	Challenge 1: B+ Tree Range Search Failure:
o	Issue: Range searches (e.g., game_id 1 to 8) returned "No games found" in the B+ Tree.
o	Solution: Fixed the range_search method to traverse all relevant nodes and corrected the split_child method to properly distribute keys.

•	Challenge 2: Incorrect Index Selection:
o	Issue: The system chose the Hash Index even when the B+ Tree was faster (e.g., 0.030s vs. 0.100s).
o	Solution: Modified benchmark_workload to select the index based on runtime and adjusted the update_query_stats threshold to 90% for equality queries.

•	Challenge 3: B+ Tree Equality Search Failure:
o	Issue: Equality search for game_id=500 returned "Game 500 not found" despite the game existing.
o	Solution: Fixed the search method to scan all keys in the leaf node, ensuring the key is found.

5. Analysis
4.1. Performance Comparison
•	Equality Searches:
o	Hash Index: O(1) average-case time complexity, making it faster for equality searches.
o	B+ Tree: O(log n) time complexity, slower but now functional after the fix.

•	Range Searches:
o	B+ Tree: Highly efficient due to its ordered structure (O(log n + k), where k is the number of keys in the range).
o	Hash Index: Inefficient (O(n)) as it scans the entire dictionary.

•	Mixed Workloads:
o	The B+ Tree outperforms the Hash Index for mixed workloads (0.030s vs. 0.100s), as it handles both types of searches well.

4.2. Adaptive Mechanism
•	The adaptive mechanism now correctly selects the B+ Tree when it performs better, ensuring optimal query performance.
•	The threshold adjustment (90% equality queries for Hash Index) favors the B+ Tree for mixed workloads, which aligns with the benchmark results.

5. Conclusion
5.1. Summary
The Game Management System successfully implements a hybrid indexing mechanism using a B+ Tree and a Hash Index. All major issues were resolved:
•	B+ Tree range and equality searches now work correctly.
•	The adaptive mechanism selects the best index based on performance.
•	The system provides a user-friendly interface for game management and performance analysis.

5.2. Achievements
•	Implemented and debugged a B+ Tree for range and equality searches.
•	Developed an adaptive indexing system that optimizes query performance.
•	Created a functional web application with user authentication and game management features.

5.3. Future Work
•	Scalability: Test with larger datasets (e.g., 1 million games) to evaluate performance.
•	Persistence: Store query_stats in the database to persist across server restarts.
•	Enhanced Adaptivity: Use a moving average of runtimes for dynamic index selection during searches.

