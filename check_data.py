# check_data.py
from app import app
from models import db, LongTermGoal, Tree, Habit, User

with app.app_context():
    print("=" * 50)
    print("DATABASE CHECK")
    print("=" * 50)
    
    # Users
    users = User.query.all()
    print(f"\nUsers: {len(users)}")
    for user in users:
        print(f"   - {user.name} ({user.email})")
    
    # Goals
    goals = LongTermGoal.query.all()
    print(f"\nGoals: {len(goals)}")
    for goal in goals:
        print(f"   - {goal.title} (Active: {goal.is_active})")
    
    # Trees
    trees = Tree.query.all()
    print(f"\nTrees: {len(trees)}")
    for tree in trees:
        print(f"   - {tree.name} (Stage: {tree.stage}, Points: {tree.growth_points})")
    
    # Habits
    habits = Habit.query.all()
    print(f"\nHabits: {len(habits)}")
    for habit in habits:
        print(f"   - {habit.name} (Frequency: {habit.frequency})")
    
    print("\n" + "=" * 50)
    print("Check complete!")