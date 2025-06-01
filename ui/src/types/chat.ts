export interface Product {
  name: string;
  price: string;
  imageUrl: string;
  description: string;
  link?: string;
  shop: string;
}

export interface SocialMediaPost {
  id: string;
  username: string;
  userAvatar: string;
  imageUrl: string;
  caption: string;
  link: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  images?: string[];
  products?: Product[];
  posts?: SocialMediaPost[];
} 