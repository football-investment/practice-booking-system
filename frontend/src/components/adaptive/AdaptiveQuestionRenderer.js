import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import MatchingQuestion from './MatchingQuestion';
import CalculationQuestion from './CalculationQuestion';
import ScenarioQuestion from './ScenarioQuestion';
import ShortAnswerQuestion from './ShortAnswerQuestion';
import LongAnswerQuestion from './LongAnswerQuestion';
import './AdaptiveQuestionRenderer.css';

const AdaptiveQuestionRenderer = ({ 
  question, 
  userAnswer, 
  onAnswerChange, 
  onSubmit, 
  isSubmitted = false,
  showFeedback = false,
  timeRemaining = null,
  difficulty = 0.5
}) => {
  const { theme, colorScheme } = useTheme();
  const [currentAnswer, setCurrentAnswer] = useState(userAnswer || null);
  const [answerStartTime] = useState(Date.now());

  useEffect(() => {
    setCurrentAnswer(userAnswer);
  }, [userAnswer]);

  const handleAnswerChange = (answer) => {
    // Prevent unnecessary re-renders if the answer hasn't actually changed
    if (answer === currentAnswer) {
      return;
    }
    
    // console.log('handleAnswerChange called with:', answer, 'type:', typeof answer);
    setCurrentAnswer(answer);
    // console.log('currentAnswer set to:', answer);
    
    if (onAnswerChange) {
      onAnswerChange(answer, {
        timeSpent: (Date.now() - answerStartTime) / 1000,
        difficulty: difficulty,
        questionId: question.id
      });
    }
  };

  const handleSubmit = () => {
    if (onSubmit && currentAnswer) {
      onSubmit(currentAnswer, {
        timeSpent: (Date.now() - answerStartTime) / 1000,
        difficulty: difficulty,
        questionId: question.id
      });
    }
  };

  const renderLegacyQuestionTypes = () => {
    switch (question.question_type) {
      case 'multiple_choice':
        return (
          <div className="multiple-choice-options">
            {question.answer_options?.map(option => (
              <label key={option.id} className="option-label">
                <input
                  type="radio"
                  name={`question-${question.id}`}
                  value={option.id}
                  checked={currentAnswer === option.id.toString()}
                  onChange={(e) => {
                    e.stopPropagation();
                    handleAnswerChange(e.target.value);
                  }}
                  disabled={isSubmitted}
                />
                <span className="option-text">{option.text || option.option_text}</span>
                {showFeedback && option.is_correct && (
                  <span className="correct-indicator">✓</span>
                )}
              </label>
            ))}
          </div>
        );

      case 'true_false':
        return (
          <div className="true-false-options">
            {question.answer_options?.map(option => (
              <button
                key={option.id}
                className={`tf-button ${currentAnswer === option.id.toString() ? 'selected' : ''}`}
                onClick={(e) => {
                  e.stopPropagation();
                  handleAnswerChange(option.id.toString());
                }}
                disabled={isSubmitted}
              >
                {option.text || option.option_text}
                {showFeedback && option.is_correct && (
                  <span className="correct-indicator">✓</span>
                )}
              </button>
            ))}
          </div>
        );

      case 'fill_in_blank':
        return (
          <div className="fill-blank-container">
            <select
              value={currentAnswer || ''}
              onChange={(e) => {
                e.stopPropagation();
                handleAnswerChange(e.target.value);
              }}
              disabled={isSubmitted}
              className="fill-blank-select"
            >
              <option value="">Select an answer...</option>
              {question.answer_options?.map(option => (
                <option key={option.id} value={option.id}>
                  {option.text || option.option_text}
                </option>
              ))}
            </select>
            {showFeedback && question.answer_options?.find(opt => 
              opt.id.toString() === currentAnswer && opt.is_correct
            ) && (
              <span className="correct-indicator">✓ Correct!</span>
            )}
          </div>
        );

      default:
        return <div className="unsupported-question">Unsupported question type: {question.question_type}</div>;
    }
  };

  const renderNewQuestionTypes = () => {
    // console.log('renderNewQuestionTypes called with question_type:', question.question_type);
    const questionProps = {
      question,
      userAnswer: currentAnswer,
      onAnswerChange: handleAnswerChange,
      onSubmit: handleSubmit,
      isSubmitted,
      showFeedback,
      timeRemaining,
      difficulty
    };

    switch (question.question_type) {
      case 'matching':
        return <MatchingQuestion {...questionProps} />;
      
      case 'calculation':
        return <CalculationQuestion {...questionProps} />;
      
      case 'scenario_based':
        return <ScenarioQuestion {...questionProps} />;
      
      case 'short_answer':
        return <ShortAnswerQuestion {...questionProps} />;
      
      case 'long_answer':
        return <LongAnswerQuestion {...questionProps} />;
      
      default:
        return renderLegacyQuestionTypes();
    }
  };

  if (!question) {
    return <div className="question-error">No question data provided</div>;
  }

  return (
    <div className={`adaptive-question-renderer ${theme}`} data-color-scheme={colorScheme}>
      <div className="question-header">
        <div className="question-meta">
          <span className="question-number">Question {question.order_index || 1}</span>
          <span className="question-type">{question.question_type.replace('_', ' ')}</span>
          {difficulty && (
            <span className={`difficulty-indicator difficulty-${Math.round(difficulty * 5)}`}>
              {'★'.repeat(Math.round(difficulty * 5))}
            </span>
          )}
          {timeRemaining && (
            <span className="time-remaining">
              {Math.floor(timeRemaining / 60)}:{String(timeRemaining % 60).padStart(2, '0')}
            </span>
          )}
        </div>
      </div>

      <div className="question-content">
        <h3 className="question-text">{question.question_text}</h3>
        
        {question.description && (
          <p className="question-description">{question.description}</p>
        )}

        <div className="answer-section">
          {renderNewQuestionTypes()}
        </div>

        {!isSubmitted && currentAnswer && (
          <div className="question-actions">
            <button 
              className="submit-button"
              onClick={handleSubmit}
              disabled={!currentAnswer}
            >
              Submit Answer
            </button>
          </div>
        )}

        {showFeedback && (
          <div className="question-feedback">
            {question.explanation && (
              <div className="explanation">
                <h4>Explanation:</h4>
                <p>{question.explanation}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdaptiveQuestionRenderer;