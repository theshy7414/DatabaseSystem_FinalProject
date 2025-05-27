export interface Product {
  name: string;
  price: string;
  imageUrl: string;
  description: string;
  link?: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  images?: string[];
  products?: Product[];
} 