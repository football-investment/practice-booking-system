import React, { useState, useEffect, useRef } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import './CalculationQuestion.css';

const CalculationQuestion = ({ 
  question, 
  userAnswer, 
  onAnswerChange, 
  isSubmitted = false,
  showFeedback = false 
}) => {
  const { theme, colorScheme } = useTheme();
  const [answer, setAnswer] = useState('');
  const [calculation, setCalculation] = useState('');
  const [showCalculator, setShowCalculator] = useState(false);
  const [calculatorExpression, setCalculatorExpression] = useState('');
  const [calculatorResult, setCalculatorResult] = useState('');
  const inputRef = useRef(null);

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
    
    // Allow numbers, decimal points, and basic math symbols
    const validPattern = /^-?[\d+\-*/().\s]*$/;
    if (validPattern.test(value) || value === '') {
      setAnswer(value);
    }
  };

  const handleCalculatorClick = (value) => {
    if (value === '=') {
      calculateResult();
    } else if (value === 'C') {
      setCalculatorExpression('');
      setCalculatorResult('');
    } else if (value === '⌫') {
      setCalculatorExpression(prev => prev.slice(0, -1));
    } else if (value === 'Use') {
      setAnswer(calculatorResult);
      setShowCalculator(false);
    } else {
      setCalculatorExpression(prev => prev + value);
    }
  };

  const calculateResult = () => {
    try {
      // Safe evaluation of mathematical expressions
      const result = evaluateExpression(calculatorExpression);
      setCalculatorResult(result.toString());
    } catch (error) {
      setCalculatorResult('Error');
    }
  };

  // Safe mathematical expression evaluator
  const evaluateExpression = (expr) => {
    // Remove spaces and validate expression
    const cleanExpr = expr.replace(/\s/g, '');
    
    // Check for valid characters only
    const validChars = /^[0-9+\-*/().\s]+$/;
    if (!validChars.test(cleanExpr)) {
      throw new Error('Invalid characters');
    }
    
    // Basic validation for balanced parentheses
    const openParens = (cleanExpr.match(/\(/g) || []).length;
    const closeParens = (cleanExpr.match(/\)/g) || []).length;
    if (openParens !== closeParens) {
      throw new Error('Unbalanced parentheses');
    }
    
    // Use Function constructor for safe evaluation (avoid eval)
    try {
      return new Function(`"use strict"; return (${cleanExpr})`)();
    } catch (e) {
      throw new Error('Invalid expression');
    }
  };

  const formatNumber = (num) => {
    if (num === null || num === undefined || num === '') return '';
    
    const parsed = parseFloat(num);
    if (isNaN(parsed)) return num;
    
    // Round to reasonable decimal places
    return Number(parsed.toFixed(10)).toString();
  };

  const checkAnswer = () => {
    if (!showFeedback || !question.correct_answer) return null;
    
    const userNum = parseFloat(answer);
    const correctNum = parseFloat(question.correct_answer);
    
    if (isNaN(userNum) || isNaN(correctNum)) return null;
    
    // Allow for small floating point errors
    const tolerance = question.tolerance || 0.01;
    const isCorrect = Math.abs(userNum - correctNum) <= tolerance;
    
    return isCorrect;
  };

  const isAnswerCorrect = checkAnswer();

  const calculatorButtons = [
    ['C', '⌫', '(', ')'],
    ['7', '8', '9', '/'],
    ['4', '5', '6', '*'],
    ['1', '2', '3', '-'],
    ['0', '.', '=', '+']
  ];

  return (
    <div className={`calculation-question ${theme}`} data-color-scheme={colorScheme}>
      <div className="calculation-container">
        
        {/* Math formula display */}
        {question.formula && (
          <div className="formula-display">
            <h4>Formula:</h4>
            <div className="formula-text">{question.formula}</div>
          </div>
        )}

        {/* Given values */}
        {question.given_values && (
          <div className="given-values">
            <h4>Given:</h4>
            <div className="values-list">
              {Object.entries(question.given_values).map(([key, value]) => (
                <div key={key} className="value-item">
                  <span className="variable">{key}</span> = <span className="value">{value}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Answer input */}
        <div className="answer-input-section">
          <label htmlFor="calculation-answer" className="answer-label">
            Your Answer:
          </label>
          <div className="input-group">
            <input
              ref={inputRef}
              id="calculation-answer"
              type="text"
              value={answer}
              onChange={handleAnswerChange}
              disabled={isSubmitted}
              className={`answer-input ${isSubmitted ? 'submitted' : ''} 
                         ${showFeedback ? (isAnswerCorrect ? 'correct' : 'incorrect') : ''}`}
              placeholder="Enter your calculation result..."
              autoComplete="off"
            />
            
            {question.unit && (
              <span className="unit-display">{question.unit}</span>
            )}
            
            <button
              type="button"
              className="calculator-toggle"
              onClick={() => setShowCalculator(!showCalculator)}
              disabled={isSubmitted}
              title="Toggle Calculator"
            >
              🧮
            </button>
          </div>

          {/* Input hints */}
          <div className="input-hints">
            <p>You can enter mathematical expressions (e.g., 2 * 3.14 * 5)</p>
            {question.decimal_places && (
              <p>Round your answer to {question.decimal_places} decimal places</p>
            )}
          </div>
        </div>

        {/* Calculator */}
        {showCalculator && !isSubmitted && (
          <div className="calculator-widget">
            <div className="calculator-display">
              <div className="expression">{calculatorExpression || '0'}</div>
              {calculatorResult && (
                <div className="result">= {calculatorResult}</div>
              )}
            </div>
            
            <div className="calculator-buttons">
              {calculatorButtons.map((row, rowIndex) => (
                <div key={rowIndex} className="button-row">
                  {row.map((btn) => (
                    <button
                      key={btn}
                      className={`calc-button ${btn === '=' ? 'equals' : ''} 
                                 ${btn === 'C' || btn === '⌫' ? 'clear' : ''}`}
                      onClick={() => handleCalculatorClick(btn)}
                    >
                      {btn}
                    </button>
                  ))}
                </div>
              ))}
            </div>
            
            {calculatorResult && calculatorResult !== 'Error' && (
              <button
                className="use-result-button"
                onClick={() => handleCalculatorClick('Use')}
              >
                Use Result ({calculatorResult})
              </button>
            )}
          </div>
        )}

        {/* Working area */}
        <div className="working-area">
          <h4>Show Your Work:</h4>
          <textarea
            value={calculation}
            onChange={(e) => setCalculation(e.target.value)}
            disabled={isSubmitted}
            className="calculation-textarea"
            placeholder="Write your calculation steps here (optional)..."
            rows={4}
          />
        </div>

        {/* Feedback */}
        {showFeedback && (
          <div className="calculation-feedback">
            <div className={`feedback-result ${isAnswerCorrect ? 'correct' : 'incorrect'}`}>
              {isAnswerCorrect ? (
                <div className="correct-feedback">
                  <span className="feedback-icon">✓</span>
                  <span>Correct! Your answer is right.</span>
                </div>
              ) : (
                <div className="incorrect-feedback">
                  <span className="feedback-icon">✗</span>
                  <span>Incorrect. The correct answer is {formatNumber(question.correct_answer)} {question.unit || ''}</span>
                </div>
              )}
            </div>

            {question.solution_steps && (
              <div className="solution-steps">
                <h4>Solution Steps:</h4>
                <ol className="steps-list">
                  {question.solution_steps.map((step, index) => (
                    <li key={index} className="solution-step">
                      {step}
                    </li>
                  ))}
                </ol>
              </div>
            )}

            {question.explanation && (
              <div className="explanation">
                <h4>Explanation:</h4>
                <p>{question.explanation}</p>
              </div>
            )}
          </div>
        )}

        {/* Mathematical reference */}
        {question.reference_formulas && (
          <div className="reference-section">
            <details>
              <summary>Reference Formulas</summary>
              <div className="reference-formulas">
                {question.reference_formulas.map((formula, index) => (
                  <div key={index} className="reference-formula">
                    <strong>{formula.name}:</strong> {formula.formula}
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
      </div>
    </div>
  );
};

export default CalculationQuestion;