import '@testing-library/jest-dom/vitest'
import { beforeEach } from 'vitest'

beforeEach(() => {
  document.cookie = 'csrftoken=test-csrf-token'
})

