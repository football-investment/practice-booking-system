import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import './MatchingQuestion.css';

const MatchingQuestion = ({ 
  question, 
  userAnswer, 
  onAnswerChange, 
  isSubmitted = false,
  showFeedback = false 
}) => {
  const { theme, colorScheme } = useTheme();
  const [matches, setMatches] = useState({});
  const [draggedItem, setDraggedItem] = useState(null);
  const [dragOverTarget, setDragOverTarget] = useState(null);

  // Parse question data for matching pairs
  const leftItems = question.answer_options?.filter(opt => opt.option_type === 'left') || [];
  const rightItems = question.answer_options?.filter(opt => opt.option_type === 'right') || [];
  
  // If no option_type specified, split items evenly
  const allItems = question.answer_options || [];
  const finalLeftItems = leftItems.length > 0 ? leftItems : allItems.slice(0, Math.ceil(allItems.length / 2));
  const finalRightItems = rightItems.length > 0 ? rightItems : allItems.slice(Math.ceil(allItems.length / 2));

  useEffect(() => {
    if (userAnswer) {
      try {
        const parsedAnswer = typeof userAnswer === 'string' ? JSON.parse(userAnswer) : userAnswer;
        setMatches(parsedAnswer || {});
      } catch (e) {
        setMatches({});
      }
    }
  }, [userAnswer]);

  useEffect(() => {
    if (onAnswerChange) {
      onAnswerChange(JSON.stringify(matches));
    }
  }, [matches, onAnswerChange]);

  const handleDragStart = (e, item) => {
    setDraggedItem(item);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.outerHTML);
    e.dataTransfer.setDragImage(e.target, 20, 20);
  };

  const handleDragOver = (e, targetItem) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverTarget(targetItem);
  };

  const handleDragLeave = () => {
    setDragOverTarget(null);
  };

  const handleDrop = (e, targetItem) => {
    e.preventDefault();
    setDragOverTarget(null);
    
    if (draggedItem && targetItem && !isSubmitted) {
      createMatch(draggedItem, targetItem);
    }
    setDraggedItem(null);
  };

  const createMatch = (leftItem, rightItem) => {
    const newMatches = { ...matches };
    
    // Remove any existing matches for these items
    Object.keys(newMatches).forEach(key => {
      if (newMatches[key] === rightItem.id || parseInt(key) === leftItem.id) {
        delete newMatches[key];
      }
    });
    
    // Create new match
    newMatches[leftItem.id] = rightItem.id;
    setMatches(newMatches);
  };

  const removeMatch = (leftItemId) => {
    if (isSubmitted) return;
    
    const newMatches = { ...matches };
    delete newMatches[leftItemId];
    setMatches(newMatches);
  };

  const getMatchedRightItem = (leftItemId) => {
    const rightItemId = matches[leftItemId];
    return finalRightItems.find(item => item.id === rightItemId);
  };

  const isRightItemMatched = (rightItemId) => {
    return Object.values(matches).includes(rightItemId);
  };

  const getCorrectMatches = () => {
    // This would come from the backend - correct answer pairs
    // For now, we'll assume the question has correct_matches property
    return question.correct_matches || {};
  };

  const isMatchCorrect = (leftItemId, rightItemId) => {
    const correctMatches = getCorrectMatches();
    return correctMatches[leftItemId] === rightItemId;
  };

  return (
    <div className={`matching-question ${theme}`} data-color-scheme={colorScheme}>
      <div className="matching-container">
        <div className="matching-columns">
          {/* Left Column */}
          <div className="left-column">
            <h4 className="column-header">Items to Match</h4>
            <div className="items-list">
              {finalLeftItems.map(item => {
                const matchedItem = getMatchedRightItem(item.id);
                const isCorrect = showFeedback && matchedItem && 
                  isMatchCorrect(item.id, matchedItem.id);
                const isIncorrect = showFeedback && matchedItem && 
                  !isMatchCorrect(item.id, matchedItem.id);

                return (
                  <div 
                    key={item.id}
                    className={`matching-item left-item ${matchedItem ? 'matched' : ''} 
                               ${isCorrect ? 'correct' : ''} ${isIncorrect ? 'incorrect' : ''}`}
                    draggable={!isSubmitted}
                    onDragStart={(e) => handleDragStart(e, item)}
                  >
                    <div className="item-content">
                      <span className="item-text">{item.option_text}</span>
                      {matchedItem && (
                        <div className="match-indicator">
                          <span className="matched-with">→ {matchedItem.option_text}</span>
                          {!isSubmitted && (
                            <button 
                              className="remove-match"
                              onClick={() => removeMatch(item.id)}
                              aria-label="Remove match"
                            >
                              ×
                            </button>
                          )}
                        </div>
                      )}
                    </div>
                    {showFeedback && (
                      <div className="feedback-indicator">
                        {isCorrect && <span className="correct-icon">✓</span>}
                        {isIncorrect && <span className="incorrect-icon">✗</span>}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right Column */}
          <div className="right-column">
            <h4 className="column-header">Match With</h4>
            <div className="items-list">
              {finalRightItems.map(item => {
                const isMatched = isRightItemMatched(item.id);
                const isDragOver = dragOverTarget?.id === item.id;

                return (
                  <div 
                    key={item.id}
                    className={`matching-item right-item ${isMatched ? 'matched' : 'available'}
                               ${isDragOver ? 'drag-over' : ''}`}
                    onDragOver={(e) => handleDragOver(e, item)}
                    onDragLeave={handleDragLeave}
                    onDrop={(e) => handleDrop(e, item)}
                  >
                    <div className="item-content">
                      <span className="item-text">{item.option_text}</span>
                    </div>
                    {isMatched && <div className="matched-overlay">Matched</div>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Mobile-friendly alternative */}
        <div className="mobile-matching">
          <p className="mobile-instruction">
            Tap a left item, then tap a right item to create a match:
          </p>
          {/* Mobile implementation would go here */}
        </div>

        {/* Progress indicator */}
        <div className="matching-progress">
          <div className="progress-text">
            Matches: {Object.keys(matches).length} / {finalLeftItems.length}
          </div>
          <div className="progress-bar">
            <div 
              className="progress-fill"
              style={{ 
                width: `${(Object.keys(matches).length / finalLeftItems.length) * 100}%` 
              }}
            />
          </div>
        </div>

        {/* Instructions */}
        <div className="matching-instructions">
          <p>
            <strong>Instructions:</strong> Drag items from the left column and drop them 
            onto the corresponding items in the right column to create matches.
          </p>
          {!isSubmitted && Object.keys(matches).length < finalLeftItems.length && (
            <p className="instruction-hint">
              Complete all matches before submitting your answer.
            </p>
          )}
        </div>

        {/* Feedback section */}
        {showFeedback && (
          <div className="matching-feedback">
            <h4>Correct Matches:</h4>
            <div className="correct-matches-list">
              {Object.entries(getCorrectMatches()).map(([leftId, rightId]) => {
                const leftItem = finalLeftItems.find(item => item.id.toString() === leftId);
                const rightItem = finalRightItems.find(item => item.id === rightId);
                
                return (
                  <div key={leftId} className="correct-match-pair">
                    <span className="left-correct">{leftItem?.option_text}</span>
                    <span className="arrow">→</span>
                    <span className="right-correct">{rightItem?.option_text}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default MatchingQuestion;