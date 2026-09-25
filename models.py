# models.py - CLEAN VERSION
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

db = SQLAlchemy()

# ----- USER MODEL -----
class User(UserMixin, db.Model):
    """User profile with authentication"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False, unique=True)
    password_hash = db.Column(db.String(200), nullable=False)
    
    profile_photo = db.Column(db.String(500), default='default.jpg')
    bio = db.Column(db.Text)
    timezone = db.Column(db.String(50), default='UTC')
    theme = db.Column(db.String(20), default='light')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    total_points = db.Column(db.Integer, default=0)
    level = db.Column(db.Integer, default=1)
    streak_days = db.Column(db.Integer, default=0)
    last_activity_date = db.Column(db.Date)
    
    goals = db.relationship('LongTermGoal', backref='user', lazy=True, cascade='all, delete-orphan')
    habit_logs = db.relationship('HabitLog', backref='user', lazy=True)
    achievements = db.relationship('Achievement', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_level_emoji(self):
        emojis = {1: '🌱', 2: '🌿', 3: '🌳', 4: '🌲', 5: '🌴', 6: '🏆', 7: '⭐', 8: '👑', 9: '🌟', 10: '💎'}
        return emojis.get(self.calculate_level(), '🌱')
    
    def calculate_level(self):
        if self.total_points >= 5000:
            return 10
        elif self.total_points >= 4000:
            return 9
        elif self.total_points >= 3000:
            return 8
        elif self.total_points >= 2000:
            return 7
        elif self.total_points >= 1500:
            return 6
        elif self.total_points >= 1000:
            return 5
        elif self.total_points >= 700:
            return 4
        elif self.total_points >= 400:
            return 3
        elif self.total_points >= 200:
            return 2
        else:
            return 1
    
    def update_streak(self):
        today = date.today()
        all_habits = Habit.query.join(Tree).join(LongTermGoal).filter(
            LongTermGoal.user_id == self.id
        ).all()
        
        if not all_habits:
            return
        
        completed_count = 0
        total_count = 0
        
        for habit in all_habits:
            log = HabitLog.query.filter_by(
                user_id=self.id,
                habit_id=habit.id,
                date=today
            ).first()
            if log:
                total_count += 1
                if log.completed:
                    completed_count += 1
        
        if total_count > 0 and completed_count == total_count:
            if self.last_activity_date == today:
                pass
            elif self.last_activity_date == today - relativedelta(days=1):
                self.streak_days += 1
            else:
                self.streak_days = 1
            self.last_activity_date = today
        else:
            if self.last_activity_date != today:
                self.streak_days = 0
        
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.name} ({self.email})>'


# ----- ACHIEVEMENT -----
class Achievement(db.Model):
    """Badges earned by the user"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(20))
    earned_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'


# ----- LONG TERM GOAL -----
class LongTermGoal(db.Model):
    """The ultimate destination (5-10 year vision)"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    target_years = db.Column(db.Integer, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    trees = db.relationship('Tree', backref='goal', lazy='dynamic', cascade='all, delete-orphan')
    
    def get_progress(self):
        """Calculate progress based on completed trees"""
        # FIXED: Use len() for lazy='dynamic' or count directly
        total_trees = self.trees.count()
        if total_trees == 0:
            return 0
        completed_trees = self.trees.filter_by(is_completed=True).count()
        return (completed_trees / total_trees) * 100
    
    def __repr__(self):
        return f'<Goal {self.title}>'


# ----- TREE (ONLY ONE DECLARATION) -----
class Tree(db.Model):
    """A tree (station/milestone)"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    order = db.Column(db.Integer, default=0)
    
    planted_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    growth_points = db.Column(db.Integer, default=0)
    stage = db.Column(db.Integer, default=0)
    is_completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    
    goal_id = db.Column(db.Integer, db.ForeignKey('long_term_goal.id'), nullable=False)
    habits = db.relationship('Habit', backref='tree', lazy=True, cascade='all, delete-orphan')
    
    def get_stage_name(self):
        stages = ['Seed', 'Sprout', 'Sapling', 'Young Tree', 'Strong Tree', 'Fruiting Tree']
        return stages[self.stage] if self.stage < len(stages) else 'Unknown'
    
    def get_stage_emoji(self):
        emojis = ['🌰', '🌱', '🌿', '🌳', '🌲', '🍎']
        return emojis[self.stage] if self.stage < len(emojis) else '🌱'
    
    def get_days_since_planted(self):
        today = date.today()
        return (today - self.planted_at.date()).days
    
    def get_planted_date_formatted(self):
        return self.planted_at.strftime('%b %d, %Y')
    
    def calculate_stage(self):
        if self.growth_points >= 200:
            return 5
        elif self.growth_points >= 150:
            return 4
        elif self.growth_points >= 100:
            return 3
        elif self.growth_points >= 60:
            return 2
        elif self.growth_points >= 30:
            return 1
        else:
            return 0
    
    def update_stage(self):
        new_stage = self.calculate_stage()
        if new_stage != self.stage:
            self.stage = new_stage
            if self.stage >= 5:
                self.is_completed = True
                self.completed_at = datetime.utcnow()
            return True
        return False
    
    def get_progress(self):
        return min((self.growth_points / 200) * 100, 100)
    
    def __repr__(self):
        return f'<Tree {self.name} ({self.get_stage_emoji()})>'


# ----- HABIT (ONLY ONE DECLARATION - WITH nullable=True FOR STANDALONE) -----
# ----- HABIT -----
class Habit(db.Model):
    """A daily action - can be attached to a tree OR standalone"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    frequency = db.Column(db.String(20), default='daily')
    custom_days = db.Column(db.String(200))
    
    points = db.Column(db.Integer, default=10)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Attached to a tree (nullable for standalone habits)
    tree_id = db.Column(db.Integer, db.ForeignKey('tree.id'), nullable=True)
    
    # ⚠️ ADD THIS LINE (owner of the habit):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    
    logs = db.relationship('HabitLog', backref='habit', lazy=True, cascade='all, delete-orphan')
    
    def get_created_date_formatted(self):
        return self.created_at.strftime('%b %d, %Y')
    
    def get_days_since_created(self):
        today = date.today()
        return (today - self.created_at.date()).days
    
    def get_completion_rate(self, days=30):
        today = date.today()
        start_date = today - relativedelta(days=days)
        
        logs = HabitLog.query.filter(
            HabitLog.habit_id == self.id,
            HabitLog.date >= start_date,
            HabitLog.date <= today
        ).all()
        
        total = len(logs)
        if total == 0:
            return 0
        
        completed = sum(1 for l in logs if l.completed)
        return (completed / total) * 100
    
    def get_tree_name(self):
        if self.tree_id:
            tree = Tree.query.get(self.tree_id)
            if tree:
                return tree.name
        return "🌱 Standalone"  # ← Fixed: fallback for standalone habits
    
    def __repr__(self):
        return f'<Habit {self.name}>'


# ----- HABIT LOG (ONLY ONE DECLARATION) -----
class HabitLog(db.Model):
    """Daily record of habit completion"""
    id = db.Column(db.Integer, primary_key=True)
    
    date = db.Column(db.Date, nullable=False, default=date.today)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    
    reason = db.Column(db.Text)
    note = db.Column(db.Text)
    
    points_earned = db.Column(db.Integer, default=0)
    
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    habit_id = db.Column(db.Integer, db.ForeignKey('habit.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    __table_args__ = (db.UniqueConstraint('habit_id', 'date', 'user_id', name='unique_habit_log_user'),)
    
    def __repr__(self):
        status = '✅' if self.completed else '❌'
        return f'<HabitLog {self.date} {self.habit_id} {status}>'


# ----- REFLECTION -----
class Reflection(db.Model):
    """Weekly/monthly reflections on the journey"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    content = db.Column(db.Text, nullable=False)
    reflection_type = db.Column(db.String(20), default='weekly')
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    stats = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    def __repr__(self):
        return f'<Reflection {self.title}>'