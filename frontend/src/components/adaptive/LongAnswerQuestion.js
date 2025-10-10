import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import './LongAnswerQuestion.css';

const LongAnswerQuestion = ({ 
  question, 
  userAnswer, 
  onAnswerChange, 
  isSubmitted = false,
  showFeedback = false 
}) => {
  const { theme, colorScheme } = useTheme();
  const [answer, setAnswer] = useState('');

  useEffect(() => {
    if (userAnswer) {
      setAnswer(userAnswer.toString());
    }
  }, [userAnswer]);

  useEffect(() => {
    if (onAnswerChange) {
      onAnswerChange(answer);
    }
  }, [answer, onAnswerChange]);

  const handleAnswerChange = (e) => {
    const value = e.target.value;
    
    // Enforce character limit if specified
    if (question.max_length && value.length > question.max_length) {
      return;
    }
    
    setAnswer(value);
  };

  const getWordCount = () => {
    return answer.trim() ? answer.trim().split(/\s+/).length : 0;
  };

  const getCharCount = () => {
    return answer.length;
  };

  const getRequirementStatus = () => {
    const wordCount = getWordCount();
    const minWords = question.min_words || 0;
    const maxWords = question.max_words || Infinity;
    
    return {
      meetMinimum: wordCount >= minWords,
      underMaximum: wordCount <= maxWords,
      wordCount
    };
  };

  const requirements = getRequirementStatus();

  return (
    <div className={`long-answer-question ${theme}`} data-color-scheme={colorScheme}>
      <div className="long-answer-container">
        
        {/* Requirements display */}
        {(question.min_words || question.max_words) && (
          <div className="requirements-display">
            <h4>Requirements:</h4>
            <div className="requirements-list">
              {question.min_words && (
                <div className={`requirement ${requirements.meetMinimum ? 'met' : 'unmet'}`}>
                  <span className="requirement-icon">{requirements.meetMinimum ? '✓' : '○'}</span>
                  Minimum {question.min_words} words
                </div>
              )}
              {question.max_words && (
                <div className={`requirement ${requirements.underMaximum ? 'met' : 'unmet'}`}>
                  <span className="requirement-icon">{requirements.underMaximum ? '✓' : '✗'}</span>
                  Maximum {question.max_words} words
                </div>
              )}
            </div>
          </div>
        )}

        {/* Answer input */}
        <div className="answer-input-section">
          <label htmlFor="long-answer-input" className="answer-label">
            Your Answer:
          </label>
          
          <textarea
            id="long-answer-input"
            value={answer}
            onChange={handleAnswerChange}
            disabled={isSubmitted}
            className={`answer-textarea ${isSubmitted ? 'submitted' : ''}`}
            placeholder={question.placeholder || "Write your detailed answer here..."}
            rows={question.rows || 8}
            maxLength={question.max_length || undefined}
          />

          {/* Input stats */}
          <div className="input-stats">
            <div className="stats-row">
              <span className={`word-count ${!requirements.meetMinimum ? 'warning' : ''} ${!requirements.underMaximum ? 'error' : ''}`}>
                {getWordCount()} word{getWordCount() !== 1 ? 's' : ''}
                {question.min_words && ` (min: ${question.min_words})`}
                {question.max_words && ` (max: ${question.max_words})`}
              </span>
              <span className="char-count">
                {getCharCount()}{question.max_length && ` / ${question.max_length}`} characters
              </span>
            </div>
            
            {/* Progress bar for word count */}
            {(question.min_words || question.max_words) && (
              <div className="word-progress">
                <div 
                  className="word-progress-bar"
                  style={{
                    width: `${Math.min(100, (getWordCount() / (question.max_words || question.min_words * 2)) * 100)}%`
                  }}
                />
              </div>
            )}
          </div>

          {/* Guidance */}
          {question.guidance && (
            <div className="answer-guidance">
              <h4>Writing Tips:</h4>
              <ul className="guidance-list">
                {question.guidance.map((tip, index) => (
                  <li key={index} className="guidance-item">
                    {tip}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Key points to address */}
          {question.key_points && (
            <div className="key-points">
              <h4>Key Points to Address:</h4>
              <ul className="key-points-list">
                {question.key_points.map((point, index) => (
                  <li key={index} className="key-point">
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Feedback */}
        {showFeedback && (
          <div className="long-answer-feedback">
            <div className="feedback-notice">
              <span className="feedback-icon">ℹ️</span>
              <span>This answer requires manual evaluation by an instructor.</span>
            </div>

            {question.sample_answer && (
              <div className="sample-answer">
                <h4>Sample Answer:</h4>
                <div className="sample-text">
                  {question.sample_answer}
                </div>
              </div>
            )}

            {question.grading_criteria && (
              <div className="grading-criteria">
                <h4>Grading Criteria:</h4>
                <ul className="criteria-list">
                  {question.grading_criteria.map((criterion, index) => (
                    <li key={index} className="criterion">
                      <strong>{criterion.category}:</strong> {criterion.description}
                      {criterion.points && (
                        <span className="points">({criterion.points} points)</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {question.explanation && (
              <div className="explanation">
                <h4>Additional Information:</h4>
                <p>{question.explanation}</p>
              </div>
            )}
          </div>
        )}

        {/* Writing tools */}
        <div className="writing-tools">
          <details>
            <summary>Writing Tools</summary>
            <div className="tools-content">
              <button 
                className="tool-button"
                onClick={() => {
                  const textarea = document.getElementById('long-answer-input');
                  const text = textarea.value;
                  const words = text.trim().split(/\s+/).filter(word => word.length > 0);
                  const sentences = text.split(/[.!?]+/).filter(s => s.trim().length > 0);
                  
                  alert(`Text Analysis:\n• Words: ${words.length}\n• Sentences: ${sentences.length}\n• Average words per sentence: ${words.length > 0 ? Math.round(words.length / Math.max(sentences.length, 1)) : 0}`);
                }}
                disabled={isSubmitted}
              >
                📊 Analyze Text
              </button>
              
              <button 
                className="tool-button"
                onClick={() => {
                  const textarea = document.getElementById('long-answer-input');
                  textarea.style.fontSize = textarea.style.fontSize === '18px' ? '16px' : '18px';
                }}
                disabled={isSubmitted}
              >
                🔍 Toggle Font Size
              </button>
              
              <button 
                className="tool-button"
                onClick={() => {
                  if (answer.trim()) {
                    navigator.clipboard.writeText(answer);
                    alert('Answer copied to clipboard!');
                  }
                }}
              >
                📋 Copy Text
              </button>
            </div>
          </details>
        </div>
      </div>
    </div>
  );
};

export default LongAnswerQuestion;