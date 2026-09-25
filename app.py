# app.py - COMPLETE WORKING VERSION
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from models import db, User, LongTermGoal, Tree, Habit, HabitLog
import os

# Create the Flask app
app = Flask(__name__)

# Configure the app
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///habits.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'

# Initialize the database
db.init_app(app)

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'# type: ignore
login_manager.login_message = 'Please log in to access this page.'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables
with app.app_context():
    db.create_all()
    print("✅ Database tables ready!")

# ----- HELPER FUNCTIONS -----

def get_growth_points_for_completion(completion_rate):
    if completion_rate >= 100:
        return 5
    elif completion_rate >= 75:
        return 3
    elif completion_rate >= 50:
        return 1
    else:
        return 0

def update_tree_growth(tree_id):
    tree = Tree.query.get(tree_id)
    if not tree:
        return
    
    today = date.today()
    habits = Habit.query.filter_by(tree_id=tree.id).all()
    
    if not habits:
        return
    
    completed = 0
    total = 0
    
    for habit in habits:
        log = HabitLog.query.filter_by(habit_id=habit.id, date=today).first()
        if log:
            total += 1
            if log.completed:
                completed += 1
    
    if total == 0:
        return
    
    completion_rate = (completed / total) * 100
    
    growth_points = get_growth_points_for_completion(completion_rate)
    tree.growth_points += growth_points
    
    stage_changed = tree.update_stage()
    
    if tree.growth_points >= 200 and not tree.is_completed:
        tree.is_completed = True
        tree.completed_at = datetime.utcnow()
    
    db.session.commit()
    return stage_changed

# ----- AUTH ROUTES -----

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Check if user has any goals
            has_goals = LongTermGoal.query.filter_by(user_id=user.id).count() > 0
            
            if not has_goals:
                flash('🌱 Welcome! Let\'s set up your first goal.', 'info')
                return redirect(url_for('welcome_wizard'))
            else:
                flash(f'👋 Welcome back, {user.name}!', 'success')
                return redirect(url_for('home'))
        else:
            flash('❌ Invalid email or password', 'error')
    
    return render_template('login.html')



@app.route('/welcome')
@login_required
def welcome_wizard():
    """Step 1: Welcome page - Create your first goal"""
    return render_template('welcome.html', user=current_user)

@app.route('/welcome/goal', methods=['GET', 'POST'])
@login_required
def welcome_goal():
    """Step 2: Create first goal"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        target_years = int(request.form.get('target_years', 10))
        
        goal = LongTermGoal()
        goal.title = title
        goal.description = description
        goal.target_years = target_years
        goal.user_id = current_user.id
        goal.is_active = True
        
        db.session.add(goal)
        db.session.commit()
        
        session['current_goal_id'] = goal.id
        flash(f'🎯 Goal "{title}" created! Now add your first tree.', 'success')
        return redirect(url_for('welcome_tree'))
    
    return render_template('welcome_goal.html', user=current_user)

@app.route('/welcome/tree', methods=['GET', 'POST'])
@login_required
def welcome_tree():
    """Step 3: Add first tree (station)"""
    goal_id = session.get('current_goal_id')
    if not goal_id:
        return redirect(url_for('welcome_goal'))
    
    goal = LongTermGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        tree = Tree()
        tree.name = name
        tree.description = description
        tree.order = 1
        tree.goal_id = goal.id
        
        db.session.add(tree)
        db.session.commit()
        
        session['current_tree_id'] = tree.id
        flash(f'🌳 Tree "{tree.name}" planted! Now add your first habit.', 'success')
        return redirect(url_for('welcome_habit'))
    
    return render_template('welcome_tree.html', goal=goal, user=current_user)

@app.route('/welcome/habit', methods=['GET', 'POST'])
@login_required
def welcome_habit():
    """Step 4: Add first habit"""
    tree_id = session.get('current_tree_id')
    if not tree_id:
        return redirect(url_for('welcome_tree'))
    
    tree = Tree.query.get_or_404(tree_id)
    if tree.goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        frequency = request.form.get('frequency', 'daily')
        points = int(request.form.get('points', 10))
        
        habit = Habit()
        habit.name = name
        habit.description = description
        habit.frequency = frequency
        habit.points = points
        habit.tree_id = tree.id
        
        db.session.add(habit)
        db.session.commit()
        
        # Clear session
        session.pop('current_goal_id', None)
        session.pop('current_tree_id', None)
        
        flash('🎉 You\'re all set! Welcome to your dashboard.', 'success')
        return redirect(url_for('home'))
    
    return render_template('welcome_habit.html', tree=tree, user=current_user)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        user = User()
        user.name = name
        user.email = email
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('✅ Account created! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# ----- HOME -----

@app.route('/home')
@login_required
def home():
    """Home page - Dashboard"""
    goals = LongTermGoal.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    goal_data = []
    for goal in goals:
        trees = Tree.query.filter_by(goal_id=goal.id).all()
        total_trees = len(trees)
        completed_trees = sum(1 for t in trees if t.is_completed)
        progress = (completed_trees / total_trees * 100) if total_trees > 0 else 0
        
        goal_data.append({
            'goal': goal,
            'progress': progress,
            'trees': trees,
            'total_trees': total_trees,
            'completed_trees': completed_trees
        })
    
    today = date.today()
    habits_with_status = []
    
    all_habits = Habit.query.join(Tree).join(LongTermGoal).filter(
        LongTermGoal.user_id == current_user.id
    ).all()
    
    for habit in all_habits:
        log = HabitLog.query.filter_by(
            user_id=current_user.id,
            habit_id=habit.id,
            date=today
        ).first()
        
        if not log:
            log = HabitLog()
            log.user_id = current_user.id
            log.habit_id = habit.id
            log.date = today
            log.completed = False
            db.session.add(log)
            db.session.commit()
        
        habits_with_status.append({
            'habit': habit,
            'log': log,
            'tree': habit.tree
        })
    
    total_habits = len(habits_with_status)
    completed_habits = sum(1 for h in habits_with_status if h['log'].completed)
    
    total_progress = sum(g['progress'] for g in goal_data)
    goal_count = len(goal_data)
    overall_progress = (total_progress / goal_count) if goal_count > 0 else 0
    
    all_trees = []
    for g in goal_data:
        all_trees.extend(g['trees'])
    
    return render_template('home.html',
                        user=current_user,
                        goals=goal_data,
                        trees=all_trees,
                        habits=habits_with_status,
                        total_habits=total_habits,
                        completed_habits=completed_habits,
                        overall_progress=overall_progress)

# ----- PATH -----

@app.route('/path')
@login_required
def path_view():
    goals = LongTermGoal.query.filter_by(user_id=current_user.id, is_active=True).all()
    
    goal_data = []
    for goal in goals:
        trees = Tree.query.filter_by(goal_id=goal.id).all()  # ← Gets trees for this goal
        goal_data.append({
            'goal': goal,
            'trees': trees
        })
    
    return render_template('path.html', goals=goal_data, user=current_user)

# ----- HABITS (Table View) -----

@app.route('/habits')
@login_required
def habits_view():
    """Habits tab - Show only THIS user's habits"""
    from sqlalchemy import or_
    
    # Get all habits that belong to this user
    # Either: (a) attached to a tree owned by this user, OR (b) standalone habit owned by this user
    all_habits = Habit.query.outerjoin(Tree).outerjoin(LongTermGoal).filter(
        or_(
            LongTermGoal.user_id == current_user.id,  # Attached habits
            Habit.user_id == current_user.id          # Standalone habits
        )
    ).all()
    
    habits_data = []
    today = date.today()
    
    for habit in all_habits:
        log = HabitLog.query.filter_by(
            user_id=current_user.id,
            habit_id=habit.id,
            date=today
        ).first()
        
        if not log:
            log = HabitLog()
            log.user_id = current_user.id
            log.habit_id = habit.id
            log.date = today
            log.completed = False
            db.session.add(log)
            db.session.commit()
        
        history = HabitLog.query.filter_by(
            user_id=current_user.id,
            habit_id=habit.id
        ).order_by(HabitLog.date.desc()).limit(30).all()
        
        habits_data.append({
            'habit': habit,
            'log': log,
            'tree': habit.tree,
            'history': history,
            'tree_name': habit.get_tree_name(),
            'completion_rate': habit.get_completion_rate()
        })
    
    return render_template('habits.html',
                        user=current_user,
                        habits=habits_data,
                        today=today)

# ----- PROFILE -----

@app.route('/profile')
@login_required
def profile():
    """Profile page"""
    goals = LongTermGoal.query.filter_by(user_id=current_user.id).all()
    
    goal_data = []
    for goal in goals:
        trees = Tree.query.filter_by(goal_id=goal.id).all()
        total_trees = len(trees)
        completed_trees = sum(1 for t in trees if t.is_completed)
        progress = (completed_trees / total_trees * 100) if total_trees > 0 else 0
        
        goal_data.append({
            'goal': goal,
            'progress': progress,
            'total_trees': total_trees,
            'completed_trees': completed_trees
        })
    
    total_goals = len(goals)
    completed_goals = sum(1 for g in goals if not g.is_active)
    total_trees = 0
    completed_trees = 0
    for goal in goals:
        trees = Tree.query.filter_by(goal_id=goal.id).all()
        total_trees += len(trees)
        completed_trees += sum(1 for t in trees if t.is_completed)
    
    return render_template('profile.html',
                        user=current_user,
                        goals=goal_data,
                        total_goals=total_goals,
                        completed_goals=completed_goals,
                        total_trees=total_trees,
                        completed_trees=completed_trees)

# ----- CREATE GOAL (Wizard Flow) -----

@app.route('/create_goal', methods=['GET', 'POST'])
@login_required
def create_goal():
    """Step 1: Create a goal"""
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        target_years = int(request.form.get('target_years', 10))
        
        goal = LongTermGoal()
        goal.title = title
        goal.description = description
        goal.target_years = target_years
        goal.user_id = current_user.id
        goal.is_active = True
        
        db.session.add(goal)
        db.session.commit()
        
        session['current_goal_id'] = goal.id
        flash(f'🎯 Goal "{title}" created! Now add your first tree.', 'success')
        return redirect(url_for('add_tree_wizard'))
    
    return render_template('create_goal.html')


@app.route('/goal/<int:goal_id>/add_tree', methods=['GET', 'POST'])
@login_required
def add_tree_to_goal(goal_id):
    """Add a tree to an existing goal (not wizard)"""
    goal = LongTermGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        tree_count = Tree.query.filter_by(goal_id=goal.id).count()
        
        tree = Tree()
        tree.name = name
        tree.description = description
        tree.order = tree_count + 1
        tree.goal_id = goal.id
        tree.planted_at = datetime.utcnow()
        
        db.session.add(tree)
        db.session.commit()
        
        flash(f'🌳 Tree "{tree.name}" planted! Now add at least 3 habits.', 'success')
        return redirect(url_for('add_habits_to_tree', tree_id=tree.id))
    
    return render_template('add_tree_individual.html', goal=goal, user=current_user)


@app.route('/add_tree_wizard', methods=['GET', 'POST'])
@login_required
def add_tree_wizard():
    """Step 2: Add a tree (must have at least 1)"""
    goal_id = session.get('current_goal_id')
    if not goal_id:
        return redirect(url_for('create_goal'))
    
    goal = LongTermGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    trees = Tree.query.filter_by(goal_id=goal.id).all()
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        
        tree = Tree()
        tree.name = name
        tree.description = description
        tree.order = len(trees) + 1
        tree.goal_id = goal.id
        tree.planted_at = datetime.utcnow()
        
        db.session.add(tree)
        db.session.commit()
        
        # Check if this is the first tree
        if len(trees) == 0:
            # First tree - must add habits immediately
            session['current_tree_id'] = tree.id
            flash(f'🌳 Tree "{tree.name}" planted! Now add at least 3 habits.', 'success')
            return redirect(url_for('add_habits_wizard'))
        else:
            # Additional tree - can add habits or add another tree
            if request.form.get('add_another'):
                flash(f'🌳 Tree "{tree.name}" planted! Add another tree or add habits.', 'success')
                return redirect(url_for('add_tree_wizard'))
            else:
                session['current_tree_id'] = tree.id
                flash(f'🌳 Tree "{tree.name}" planted! Now add at least 3 habits.', 'success')
                return redirect(url_for('add_habits_wizard'))
    
    return render_template('add_tree_wizard.html', goal=goal, trees=trees, user=current_user)


@app.route('/tree/<int:tree_id>/add_habits', methods=['GET', 'POST'])
@login_required
def add_habits_to_tree(tree_id):
    """Add habits to an existing tree"""
    tree = Tree.query.get_or_404(tree_id)
    if tree.goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    habits = Habit.query.filter_by(tree_id=tree.id).all()
    habit_count = len(habits)
    habits_needed = max(0, 3 - habit_count)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        frequency = request.form.get('frequency', 'daily')
        points = int(request.form.get('points', 10))
        
        habit = Habit()
        habit.name = name
        habit.description = description
        habit.frequency = frequency
        habit.points = points
        habit.tree_id = tree.id
        habit.created_at = datetime.utcnow()
        
        db.session.add(habit)
        db.session.commit()
        
        new_count = habit_count + 1
        
        if request.form.get('add_another'):
            flash(f'💧 Habit "{habit.name}" added! Add more habits.', 'success')
            return redirect(url_for('add_habits_to_tree', tree_id=tree.id))
        else:
            if new_count >= 3:
                flash(f'✅ Tree "{tree.name}" now has {new_count} habits!', 'success')
                return redirect(url_for('view_tree', tree_id=tree.id))
            else:
                flash(f'⚠️ You need at least 3 habits per tree! You have {new_count}/3.', 'warning')
                return redirect(url_for('add_habits_to_tree', tree_id=tree.id))
    
    return render_template('add_habits_to_tree.html', 
                        tree=tree,
                        habits=habits,
                        habit_count=habit_count,
                        habits_needed=habits_needed,
                        user=current_user)


@app.route('/add_habits_wizard', methods=['GET', 'POST'])
@login_required
def add_habits_wizard():
    """Add habits to tree (minimum 3 required)"""
    tree_id = session.get('current_tree_id')
    if not tree_id:
        return redirect(url_for('add_tree_wizard'))
    
    tree = Tree.query.get_or_404(tree_id)
    if tree.goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    habits = Habit.query.filter_by(tree_id=tree.id).all()
    habit_count = len(habits)
    habits_needed = max(0, 3 - habit_count)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        frequency = request.form.get('frequency', 'daily')
        points = int(request.form.get('points', 10))
        
        habit = Habit()
        habit.name = name
        habit.description = description
        habit.frequency = frequency
        habit.points = points
        habit.tree_id = tree.id
        habit.created_at = datetime.utcnow()
        
        db.session.add(habit)
        db.session.commit()
        
        new_count = habit_count + 1
        
        if request.form.get('add_another'):
            # User wants to add another habit
            flash(f'💧 Habit "{habit.name}" added! Add more habits.', 'success')
            return redirect(url_for('add_habits_wizard'))
        else:
            # User clicked "Complete Setup"
            if new_count >= 3:
                session.pop('current_goal_id', None)
                session.pop('current_tree_id', None)
                flash('🎉 Goal setup complete! Your tree has 3+ habits and is ready to grow!', 'success')
                return redirect(url_for('home'))
            else:
                flash(f'⚠️ You need at least 3 habits per tree! You have {new_count}/3.', 'warning')
                return redirect(url_for('add_habits_wizard'))
    
    return render_template('add_habit_wizard.html', 
                        tree=tree,
                        habits=habits,
                        habit_count=habit_count,
                        habits_needed=habits_needed,
                        user=current_user)

@app.route('/add_habit/<int:tree_id>', methods=['GET', 'POST'])
@login_required
def add_habit(tree_id):
    """Add a single habit to a tree"""
    tree = Tree.query.get_or_404(tree_id)
    if tree.goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        frequency = request.form.get('frequency', 'daily')
        points = int(request.form.get('points', 10))
        
        habit = Habit()
        habit.name = name
        habit.description = description
        habit.frequency = frequency
        habit.points = points
        habit.tree_id = tree.id
        habit.created_at = datetime.utcnow()  # Set creation date
        
        db.session.add(habit)
        db.session.commit()
        
        flash(f'💧 Habit "{habit.name}" added!', 'success')
        return redirect(url_for('view_tree', tree_id=tree.id))
    
    return render_template('add_habit.html', tree=tree, user=current_user)

@app.route('/tree/<int:tree_id>')
@login_required
def view_tree(tree_id):
    """View a single tree with all its habits"""
    tree = Tree.query.get_or_404(tree_id)
    if tree.goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    habits = Habit.query.filter_by(tree_id=tree.id).all()
    
    # Get today's logs
    today = date.today()
    for habit in habits:
        log = HabitLog.query.filter_by(
            user_id=current_user.id,
            habit_id=habit.id,
            date=today
        ).first()
        if not log:
            log = HabitLog()
            log.user_id = current_user.id
            log.habit_id = habit.id
            log.date = today
            log.completed = False
            db.session.add(log)
            db.session.commit()
        habit.today_log = log
    
    return render_template('tree_detail.html', tree=tree, habits=habits, user=current_user)


# ----- TOGGLE HABIT -----


@app.route('/tree/<int:tree_id>/add_habit_single', methods=['GET', 'POST'])
@login_required
def add_habit_to_tree_single(tree_id):
    """Add a single habit to an existing tree"""
    tree = Tree.query.get_or_404(tree_id)
    if tree.goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        frequency = request.form.get('frequency', 'daily')
        points = int(request.form.get('points', 10))
        
        habit = Habit()
        habit.name = name
        habit.description = description
        habit.frequency = frequency
        habit.points = points
        habit.tree_id = tree.id
        habit.user_id = current_user.id
        habit.created_at = datetime.utcnow()
        
        db.session.add(habit)
        db.session.commit()
        
        flash(f'💧 Habit "{habit.name}" added to {tree.name}!', 'success')
        return redirect(url_for('view_tree', tree_id=tree.id))
    
    return render_template('add_habit_to_tree.html', tree=tree, user=current_user)


@app.route('/toggle_habit/<int:log_id>', methods=['POST'])
@login_required
def toggle_habit(log_id):
    """Toggle habit completion"""
    log = HabitLog.query.get_or_404(log_id)
    
    if log.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.json
    completed = data.get('completed', not log.completed)
    reason = data.get('reason', '')
    
    if completed:
        log.completed = True
        log.completed_at = datetime.utcnow()
        log.reason = None
        log.points_earned = log.habit.points
        current_user.total_points += log.habit.points
    else:
        log.completed = False
        log.completed_at = None
        log.reason = reason
        log.points_earned = 0
    
    db.session.commit()
    
    habit = Habit.query.get(log.habit_id)
    if habit:
        tree = Tree.query.get(habit.tree_id)
        if tree:
            stage_changed = update_tree_growth(tree.id)
            
            if stage_changed:
                return jsonify({
                    'success': True,
                    'completed': log.completed,
                    'stage_changed': True,
                    'new_stage': tree.stage,
                    'new_stage_name': tree.get_stage_name(),
                    'new_stage_emoji': tree.get_stage_emoji(),
                    'points_earned': log.points_earned,
                    'total_points': current_user.total_points
                })
    
    return jsonify({
        'success': True,
        'completed': log.completed,
        'points_earned': log.points_earned,
        'total_points': current_user.total_points
    })


@app.route('/add_habit_standalone', methods=['GET', 'POST'])
@login_required
def add_habit_standalone():
    """Add a standalone habit"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        frequency = request.form.get('frequency', 'daily')
        points = int(request.form.get('points', 10))
        
        habit = Habit()
        habit.name = name
        habit.description = description
        habit.frequency = frequency
        habit.points = points
        habit.tree_id = None  # Standalone
        habit.user_id = current_user.id  # FIXED: Set the owner!
        habit.created_at = datetime.utcnow()
        
        db.session.add(habit)
        db.session.commit()
        
        flash(f'💧 Habit "{habit.name}" added!', 'success')
        return redirect(url_for('habits_view'))
    
    return render_template('add_habit_standalone.html', user=current_user)
# ----- DELETE ROUTES -----

@app.route('/goal/<int:goal_id>/delete', methods=['POST'])
@login_required
def delete_goal(goal_id):
    """Delete a goal and all its trees and habits"""
    goal = LongTermGoal.query.get_or_404(goal_id)
    
    if goal.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    goal_title = goal.title
    
    trees = Tree.query.filter_by(goal_id=goal.id).all()
    for tree in trees:
        Habit.query.filter_by(tree_id=tree.id).delete()
    Tree.query.filter_by(goal_id=goal.id).delete()
    
    db.session.delete(goal)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'redirect': url_for('home')
    })


@app.route('/tree/<int:tree_id>/delete', methods=['POST'])
@login_required
def delete_tree(tree_id):
    """Delete a tree and all its habits"""
    tree = Tree.query.get_or_404(tree_id)
    
    if tree.goal.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    tree_name = tree.name
    goal_id = tree.goal_id
    
    Habit.query.filter_by(tree_id=tree.id).delete()
    db.session.delete(tree)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'redirect': url_for('view_goal', goal_id=goal_id)
    })


@app.route('/habit/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    """Delete a single habit"""
    habit = Habit.query.get_or_404(habit_id)
    
    # Check permission
    if habit.tree_id:
        tree = Tree.query.get(habit.tree_id)
        if tree and tree.goal.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
    else:
        # Standalone habit - check if it belongs to the user
        log = HabitLog.query.filter_by(habit_id=habit.id, user_id=current_user.id).first()
        if not log:
            return jsonify({'success': False, 'message': 'Permission denied'}), 403
    
    tree_id = habit.tree_id
    habit_name = habit.name
    
    db.session.delete(habit)
    db.session.commit()
    
    if tree_id:
        redirect_url = url_for('view_tree', tree_id=tree_id)
    else:
        redirect_url = url_for('habits_view')
    
    return jsonify({
        'success': True,
        'redirect': redirect_url,
        'message': f'Habit "{habit_name}" deleted successfully'
    })



# ----- VIEW GOAL -----

@app.route('/goal/<int:goal_id>')
@login_required
def view_goal(goal_id):
    goal = LongTermGoal.query.get_or_404(goal_id)
    if goal.user_id != current_user.id:
        return redirect(url_for('home'))
    
    trees = Tree.query.filter_by(goal_id=goal.id).all()
    return render_template('goal_detail.html', goal=goal, trees=trees, user=current_user)

if __name__ == '__main__':
    print("🚀 Starting Flask app on http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)

