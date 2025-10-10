import React, { useState, useEffect } from 'react';
import { useTheme } from '../../contexts/ThemeContext';
import './ScenarioQuestion.css';

const ScenarioQuestion = ({ 
  question, 
  userAnswer, 
  onAnswerChange, 
  isSubmitted = false,
  showFeedback = false 
}) => {
  const { theme, colorScheme } = useTheme();
  const [selectedChoices, setSelectedChoices] = useState([]);
  const [reasoning, setReasoning] = useState('');

  useEffect(() => {
    if (userAnswer) {
      try {
        const parsed = typeof userAnswer === 'string' ? JSON.parse(userAnswer) : userAnswer;
        setSelectedChoices(parsed.choices || []);
        setReasoning(parsed.reasoning || '');
      } catch (e) {
        setSelectedChoices([]);
        setReasoning('');
      }
    }
  }, [userAnswer]);

  useEffect(() => {
    if (onAnswerChange) {
      onAnswerChange(JSON.stringify({
        choices: selectedChoices,
        reasoning: reasoning
      }));
    }
  }, [selectedChoices, reasoning, onAnswerChange]);

  const handleChoiceToggle = (choiceId) => {
    if (isSubmitted) return;
    
    if (question.multiple_selection) {
      // Multiple choice scenario
      setSelectedChoices(prev => 
        prev.includes(choiceId) 
          ? prev.filter(id => id !== choiceId)
          : [...prev, choiceId]
      );
    } else {
      // Single choice scenario
      setSelectedChoices([choiceId]);
    }
  };

  const isChoiceSelected = (choiceId) => {
    return selectedChoices.includes(choiceId);
  };

  const getChoiceCorrectness = (choice) => {
    if (!showFeedback) return null;
    
    const isSelected = isChoiceSelected(choice.id);
    const isCorrect = choice.is_correct;
    
    if (isSelected && isCorrect) return 'correct-selected';
    if (isSelected && !isCorrect) return 'incorrect-selected';
    if (!isSelected && isCorrect) return 'correct-unselected';
    return 'neutral';
  };

  const getScenarioScore = () => {
    if (!showFeedback || !question.choices) return null;
    
    let correctSelections = 0;
    let totalCorrect = 0;
    let incorrectSelections = 0;
    
    question.choices.forEach(choice => {
      if (choice.is_correct) {
        totalCorrect++;
        if (isChoiceSelected(choice.id)) {
          correctSelections++;
        }
      } else if (isChoiceSelected(choice.id)) {
        incorrectSelections++;
      }
    });
    
    const score = Math.max(0, correctSelections - incorrectSelections);
    const maxScore = totalCorrect;
    
    return { score, maxScore, correctSelections, incorrectSelections };
  };

  const scenarioScore = getScenarioScore();

  return (
    <div className={`scenario-question ${theme}`} data-color-scheme={colorScheme}>
      <div className="scenario-container">
        
        {/* Scenario Background */}
        {question.scenario_background && (
          <div className="scenario-background">
            <h4>Scenario:</h4>
            <div className="background-text">
              {question.scenario_background}
            </div>
          </div>
        )}

        {/* Context Information */}
        {question.context_info && (
          <div className="context-info">
            <h4>Context:</h4>
            <div className="context-details">
              {Object.entries(question.context_info).map(([key, value]) => (
                <div key={key} className="context-item">
                  <strong>{key.replace(/_/g, ' ')}:</strong> {value}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Decision Point */}
        <div className="decision-point">
          <h4>Your Decision:</h4>
          <p className="decision-instruction">
            {question.multiple_selection 
              ? "Select all appropriate actions you would take in this situation:"
              : "Select the best course of action in this situation:"
            }
          </p>
        </div>

        {/* Choice Options */}
        <div className="scenario-choices">
          {question.choices?.map(choice => {
            const correctness = getChoiceCorrectness(choice);
            const isSelected = isChoiceSelected(choice.id);
            
            return (
              <div 
                key={choice.id}
                className={`scenario-choice ${isSelected ? 'selected' : ''} ${correctness || ''}`}
                onClick={() => handleChoiceToggle(choice.id)}
              >
                <div className="choice-content">
                  <div className="choice-header">
                    <div className="choice-selector">
                      {question.multiple_selection ? (
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => {}} // Handled by parent click
                          disabled={isSubmitted}
                        />
                      ) : (
                        <input
                          type="radio"
                          checked={isSelected}
                          onChange={() => {}} // Handled by parent click
                          disabled={isSubmitted}
                          name={`scenario-${question.id}`}
                        />
                      )}
                    </div>
                    <div className="choice-text">
                      {choice.option_text}
                    </div>
                  </div>
                  
                  {choice.description && (
                    <div className="choice-description">
                      {choice.description}
                    </div>
                  )}

                  {/* Choice consequences (shown after submission) */}
                  {showFeedback && choice.consequences && (
                    <div className="choice-consequences">
                      <strong>Consequences:</strong> {choice.consequences}
                    </div>
                  )}

                  {/* Feedback indicators */}
                  {showFeedback && (
                    <div className="choice-feedback">
                      {correctness === 'correct-selected' && (
                        <span className="feedback-badge correct">✓ Good choice!</span>
                      )}
                      {correctness === 'incorrect-selected' && (
                        <span className="feedback-badge incorrect">✗ Not ideal</span>
                      )}
                      {correctness === 'correct-unselected' && (
                        <span className="feedback-badge missed">! You missed this good option</span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Reasoning Section */}
        <div className="reasoning-section">
          <label htmlFor="scenario-reasoning" className="reasoning-label">
            Explain your reasoning (optional):
          </label>
          <textarea
            id="scenario-reasoning"
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            disabled={isSubmitted}
            className="reasoning-textarea"
            placeholder="Explain why you made these choices and what factors you considered..."
            rows={4}
          />
        </div>

        {/* Scenario Feedback */}
        {showFeedback && (
          <div className="scenario-feedback">
            {scenarioScore && (
              <div className="score-summary">
                <h4>Your Performance:</h4>
                <div className="score-details">
                  <div className="score-item">
                    <span className="score-label">Score:</span>
                    <span className="score-value">{scenarioScore.score} / {scenarioScore.maxScore}</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">Correct selections:</span>
                    <span className="score-value correct">{scenarioScore.correctSelections}</span>
                  </div>
                  {scenarioScore.incorrectSelections > 0 && (
                    <div className="score-item">
                      <span className="score-label">Incorrect selections:</span>
                      <span className="score-value incorrect">{scenarioScore.incorrectSelections}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {question.expert_analysis && (
              <div className="expert-analysis">
                <h4>Expert Analysis:</h4>
                <p>{question.expert_analysis}</p>
              </div>
            )}

            {question.learning_points && (
              <div className="learning-points">
                <h4>Key Learning Points:</h4>
                <ul className="learning-list">
                  {question.learning_points.map((point, index) => (
                    <li key={index} className="learning-point">
                      {point}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {question.additional_resources && (
              <div className="additional-resources">
                <h4>Additional Resources:</h4>
                <ul className="resources-list">
                  {question.additional_resources.map((resource, index) => (
                    <li key={index} className="resource-item">
                      <a 
                        href={resource.url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="resource-link"
                      >
                        {resource.title}
                      </a>
                      {resource.description && (
                        <span className="resource-description"> - {resource.description}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default ScenarioQuestion;