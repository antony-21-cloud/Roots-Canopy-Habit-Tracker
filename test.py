# test.py
from app import app
from models import db, User, LongTermGoal, Tree, Habit

with app.app_context():
    print("=" * 50)
    print("DATABASE CONTENTS")
    print("=" * 50)
    
    users = User.query.all()
    print(f"\nUsers ({len(users)}):")
    for u in users:
        print(f"  ID {u.id}: {u.email}")
    
    goals = LongTermGoal.query.all()
    print(f"\nGoals ({len(goals)}):")
    for g in goals:
        print(f"  ID {g.id}: '{g.title}' (user_id: {g.user_id})")
    
    trees = Tree.query.all()
    print(f"\nTrees ({len(trees)}):")
    for t in trees:
        print(f"  ID {t.id}: '{t.name}' (goal_id: {t.goal_id})")
    
    habits = Habit.query.all()
    print(f"\nHabits ({len(habits)}):")
    for h in habits:
        # Try to access user_id
        try:
            uid = h.user_id
        except AttributeError:
            uid = "N/A (column missing)"
        print(f"  ID {h.id}: '{h.name}' (tree_id: {h.tree_id}, user_id: {uid})")