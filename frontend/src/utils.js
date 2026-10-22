export function getErrorMessage(error) {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.';
}
