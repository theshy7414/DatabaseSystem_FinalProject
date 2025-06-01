type ToastOptions = {
  title: string;
  description: string;
  variant?: 'default' | 'destructive';
};

// Simple toast implementation - you can replace this with a proper toast library
export const toast = (options: ToastOptions) => {
  console.error(`${options.title}: ${options.description}`);
  // TODO: Implement proper toast notifications
}; 