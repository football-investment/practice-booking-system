import { render, screen } from '@testing-library/react';
import App from './App';

test('renders practice booking system app', () => {
  render(<App />);
  // Test for the unique app title in header
  const titleElement = document.querySelector('.app-title');
  expect(titleElement).toBeInTheDocument();
  expect(titleElement).toHaveTextContent('Practice Booking System');
});
