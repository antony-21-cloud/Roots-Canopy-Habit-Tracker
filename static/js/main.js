// Habit Tracker - Main JavaScript

document.addEventListener('DOMContentLoaded', function() {
    
    // ----- CHECKBOX TOGGLING -----
    const checkboxes = document.querySelectorAll('.habit-checkbox');
    const reasonModal = document.getElementById('reason-modal');
    const reasonText = document.getElementById('reason-text');
    const saveReasonBtn = document.getElementById('save-reason');
    const cancelReasonBtn = document.getElementById('cancel-reason');
    const toast = document.getElementById('toast');
    
    let currentLogId = null;
    let currentCheckbox = null;
    let toastTimeout = null;
    
    // Handle checkbox clicks
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const logId = this.dataset.logId;
            const isChecked = this.checked;
            
            if (!isChecked) {
                // If UNCHECKING, ask for reason
                currentLogId = logId;
                currentCheckbox = this;
                reasonModal.style.display = 'flex';
                reasonText.value = '';
                reasonText.focus();
                // Keep checkbox checked until reason is saved
                this.checked = true;
            } else {
                // If CHECKING, just toggle
                toggleHabit(logId, true);
            }
        });
    });
    
    // ----- REASON MODAL -----
    saveReasonBtn.addEventListener('click', function() {
        if (currentLogId) {
            const reason = reasonText.value.trim();
            if (reason) {
                // Toggle off with reason
                toggleHabit(currentLogId, false, reason);
                reasonModal.style.display = 'none';
                if (currentCheckbox) {
                    currentCheckbox.checked = false;
                }
                currentLogId = null;
                currentCheckbox = null;
            } else {
                alert('💭 Please enter a reason why you missed this habit.');
                reasonText.focus();
            }
        }
    });
    
    cancelReasonBtn.addEventListener('click', function() {
        reasonModal.style.display = 'none';
        if (currentCheckbox) {
            currentCheckbox.checked = true;
        }
        currentLogId = null;
        currentCheckbox = null;
    });
    
    // Close modal on outside click
    window.addEventListener('click', function(event) {
        if (event.target === reasonModal) {
            reasonModal.style.display = 'none';
            if (currentCheckbox) {
                currentCheckbox.checked = true;
            }
            currentLogId = null;
            currentCheckbox = null;
        }
    });
    
    // Enter key to save reason
    reasonText.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && e.ctrlKey) {
            saveReasonBtn.click();
        }
    });
    
    // ----- TOGGLE HABIT FUNCTION -----
    function toggleHabit(logId, completed, reason = '') {
        fetch(`/toggle_habit/${logId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                completed: completed,
                reason: reason
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                if (data.stage_changed) {
                    // Tree grew! Show celebration
                    showToast(`🌱 Your tree grew to ${data.new_stage_name}! ${data.new_stage_emoji}`);
                    
                    // Update the tree display on the page
                    updateTreeDisplay(data);
                } else {
                    showToast(completed ? '✅ Habit completed!' : '💭 Habit marked as missed');
                }
                
                // If the reason was saved, reload to show it
                if (reason) {
                    setTimeout(() => location.reload(), 1000);
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('❌ Something went wrong. Please try again.');
        });
    }
    
    // ----- UPDATE TREE DISPLAY -----
    function updateTreeDisplay(data) {
        // Find all tree displays and update them
        const treeCards = document.querySelectorAll('.tree-card');
        treeCards.forEach(card => {
            const treeDisplay = card.querySelector('.tree-display');
            const stageName = card.querySelector('.tree-stats span:first-child');
            const growthBar = card.querySelector('.growth-fill');
            
            if (treeDisplay) {
                // Update emoji based on new stage
                const emojis = ['🌰', '🌱', '🌿', '🌳', '🌲', '🍎'];
                treeDisplay.innerHTML = `<div class="tree-emoji">${emojis[data.new_stage]}</div>`;
            }
            
            if (stageName) {
                stageName.textContent = `Stage: ${data.new_stage_name}`;
            }
            
            if (growthBar) {
                const growthPercent = (data.growth_points / 200 * 100);
                growthBar.style.width = `${Math.min(growthPercent, 100)}%`;
            }
        });
    }
    
    // ----- SHOW TOAST -----
    function showToast(message) {
        if (toastTimeout) {
            clearTimeout(toastTimeout);
        }
        
        toast.textContent = message;
        toast.style.display = 'block';
        
        toastTimeout = setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    }
    
    // ----- REASON BUTTONS (for existing missed habits) -----
    const reasonButtons = document.querySelectorAll('.reason-btn');
    reasonButtons.forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.stopPropagation();
            const logId = this.dataset.logId;
            const habitItem = this.closest('.habit-item');
            const reasonText = habitItem.querySelector('.reason-text');
            
            if (reasonText) {
                // If reason already exists, show it
                const existingReason = reasonText.textContent.replace('💭 ', '');
                currentLogId = logId;
                reasonModal.style.display = 'flex';
                reasonText.value = existingReason;
            } else {
                // No reason yet, show empty modal
                currentLogId = logId;
                reasonModal.style.display = 'flex';
                reasonText.value = '';
            }
            
            // Update reason button behavior
            saveReasonBtn.onclick = function() {
                const newReason = reasonText.value.trim();
                if (newReason) {
                    updateReason(currentLogId, newReason);
                    reasonModal.style.display = 'none';
                } else {
                    alert('Please enter a reason.');
                }
            };
        });
    });
    
    // ----- UPDATE REASON FUNCTION -----
    function updateReason(logId, reason) {
        fetch(`/update_reason/${logId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `reason=${encodeURIComponent(reason)}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showToast('💭 Reason saved!');
                setTimeout(() => location.reload(), 1000);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showToast('❌ Error saving reason.');
        });
    }
    
    // ----- KEYBOARD SHORTCUTS -----
    document.addEventListener('keydown', function(e) {
        // Escape to close modal
        if (e.key === 'Escape' && reasonModal.style.display === 'flex') {
            cancelReasonBtn.click();
        }
    });
    
    console.log('🌱 Roots & Canopy loaded successfully!');
});
// ----- DELETE CONFIRMATION FUNCTIONS -----

function confirmDeleteGoal(goalId, goalTitle) {
    if (confirm(`⚠️ Are you sure you want to delete the goal "${goalTitle}"?\n\nThis will also delete ALL trees and habits in this goal. This action cannot be undone.`)) {
        fetch(`/goal/${goalId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect;
            } else {
                alert('❌ Error deleting goal: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('❌ An error occurred. Please try again.');
        });
    }
}

function confirmDeleteTree(treeId, treeName) {
    if (confirm(`⚠️ Are you sure you want to delete the tree "${treeName}"?\n\nThis will also delete ALL habits in this tree. This action cannot be undone.`)) {
        fetch(`/tree/${treeId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect;
            } else {
                alert('❌ Error deleting tree: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('❌ An error occurred. Please try again.');
        });
    }
}

function confirmDeleteHabit(habitId, habitName) {
    if (confirm(`⚠️ Are you sure you want to delete the habit "${habitName}"?\n\nThis action cannot be undone.`)) {
        fetch(`/habit/${habitId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                window.location.href = data.redirect;
            } else {
                alert('❌ Error deleting habit: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('❌ An error occurred. Please try again.');
        });
    }
}

// ----- DELETE HABIT FUNCTION -----
function confirmDeleteHabit(habitId, habitName) {
    if (confirm(`⚠️ Are you sure you want to delete the habit "${habitName}"?\n\nThis action cannot be undone.`)) {
        fetch(`/habit/${habitId}/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Show success message
                showToast(`🗑️ Habit "${habitName}" deleted successfully`);
                // Reload the page to refresh the list
                setTimeout(() => location.reload(), 1000);
            } else {
                alert('❌ Error deleting habit: ' + data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('❌ An error occurred. Please try again.');
        });
    }
}

// Helper function for toast notifications (if you don't have it)
function showToast(message) {
    const toast = document.getElementById('toast');
    if (toast) {
        toast.textContent = message;
        toast.style.display = 'block';
        setTimeout(() => {
            toast.style.display = 'none';
        }, 3000);
    } else {
        alert(message);
    }
}