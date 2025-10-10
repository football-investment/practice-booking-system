import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import './ShortAnswerQuestion.css';

const ShortAnswerQuestion = ({ 
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

  const checkAnswer = () => {
    if (!showFeedback || !question.correct_answers) return null;
    
    const userInput = answer.trim().toLowerCase();
    const correctAnswers = Array.isArray(question.correct_answers) 
      ? question.correct_answers 
      : [question.correct_answers];
    
    return correctAnswers.some(correct => 
      correct.toLowerCase() === userInput
    );
  };

  const isAnswerCorrect = checkAnswer();

  return (
    <div className={`short-answer-question ${theme}`} data-color-scheme={colorScheme}>
      <div className="short-answer-container">
        
        {/* Answer input */}
        <div className="answer-input-section">
          <label htmlFor="short-answer-input" className="answer-label">
            Your Answer:
          </label>
          
          <input
            id="short-answer-input"
            type="text"
            value={answer}
            onChange={handleAnswerChange}
            disabled={isSubmitted}
            className={`answer-input ${isSubmitted ? 'submitted' : ''} 
                       ${showFeedback ? (isAnswerCorrect ? 'correct' : 'incorrect') : ''}`}
            placeholder={question.placeholder || "Enter your answer..."}
            maxLength={question.max_length || undefined}
            autoComplete="off"
          />

          {/* Character/word count */}
          <div className="input-stats">
            <span className="char-count">
              {getCharCount()}{question.max_length && ` / ${question.max_length}`} characters
            </span>
            <span className="word-count">
              {getWordCount()} word{getWordCount() !== 1 ? 's' : ''}
            </span>
          </div>

          {/* Hints */}
          {question.hints && (
            <div className="answer-hints">
              {question.hints.map((hint, index) => (
                <div key={index} className="hint-item">
                  💡 {hint}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Feedback */}
        {showFeedback && (
          <div className="short-answer-feedback">
            <div className={`feedback-result ${isAnswerCorrect ? 'correct' : 'incorrect'}`}>
              {isAnswerCorrect ? (
                <div className="correct-feedback">
                  <span className="feedback-icon">✓</span>
                  <span>Correct! Well done.</span>
                </div>
              ) : (
                <div className="incorrect-feedback">
                  <span className="feedback-icon">✗</span>
                  <span>Incorrect. {question.correct_answers && `Correct answer(s): ${Array.isArray(question.correct_answers) ? question.correct_answers.join(', ') : question.correct_answers}`}</span>
                </div>
              )}
            </div>

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

export default ShortAnswerQuestion;