import { render, screen } from '@testing-library/react'
import StatusBadge from '../components/StatusBadge'

const STATUSES = ['pending', 'running', 'completed', 'aborted', 'errored'] as const

test.each(STATUSES)('renders %s status', (status) => {
  render(<StatusBadge status={status} />)
  expect(screen.getByText(status)).toBeInTheDocument()
})

test('renders unknown status without crashing', () => {
  render(<StatusBadge status="unknown_future_status" />)
  expect(screen.getByText('unknown_future_status')).toBeInTheDocument()
})

test('completed has green styling', () => {
  render(<StatusBadge status="completed" />)
  expect(screen.getByText('completed')).toHaveClass('text-green-700')
})

test('errored has red styling', () => {
  render(<StatusBadge status="errored" />)
  expect(screen.getByText('errored')).toHaveClass('text-red-700')
})

test('running has blue styling', () => {
  render(<StatusBadge status="running" />)
  expect(screen.getByText('running')).toHaveClass('text-blue-700')
})
