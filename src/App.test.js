// src/App.test.js
import { render, screen } from '@testing-library/react';
import App from './App';

test('renders ApexChain title', () => {
    render(<App />);
    const titleElement = screen.getByText(/ApexChain/i);
    expect(titleElement).toBeInTheDocument();
});
