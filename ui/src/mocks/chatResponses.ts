import type { Message } from "@/types/chat";
import { v4 as uuidv4 } from "uuid";

type MockResponse = {
  content: string;
  products?: Message['products'];
  posts?: Message['posts'];
};

const MOCK_PRODUCTS = {
  matching: [
    {
      name: "Matching Item 1",
      price: "$79.99",
      imageUrl: "https://example.com/match1.jpg",
      description: "Perfect complement to your selected item",
      link: "https://example.com/match1",
      shop: "Fashion Finds"
    },
    {
      name: "Matching Item 2",
      price: "$89.99",
      imageUrl: "https://example.com/match2.jpg",
      description: "Another great piece to complete the look",
      link: "https://example.com/match2",
      shop: "Style Studio"
    }
  ],
  similar: [
    {
      name: "Similar Item 1",
      price: "$69.99",
      imageUrl: "https://example.com/similar1.jpg",
      description: "Similar style with a unique twist",
      link: "https://example.com/similar1",
      shop: "Fashion Hub"
    },
    {
      name: "Similar Item 2",
      price: "$84.99",
      imageUrl: "https://example.com/similar2.jpg",
      description: "Another great alternative in the same style",
      link: "https://example.com/similar2",
      shop: "Style Co"
    }
  ],
  general: [
    {
      name: "Classic White Sneakers",
      price: "$89.99",
      imageUrl: "https://example.com/sneakers.jpg",
      description: "Versatile white sneakers that go with everything",
      link: "https://example.com/product",
      shop: "Urban Footwear"
    },
    {
      name: "Denim Jacket",
      price: "$129.99",
      imageUrl: "https://example.com/jacket.jpg",
      description: "Classic denim jacket perfect for layering",
      link: "https://example.com/jacket",
      shop: "Fashion District"
    },
    {
      name: "Denim Jacket",
      price: "$129.99",
      imageUrl: "https://example.com/jacket.jpg",
      description: "Classic denim jacket perfect for layering",
      link: "https://example.com/jacket",
      shop: "Fashion District"
    },
    {
      name: "Denim Jacket",
      price: "$129.99",
      imageUrl: "https://example.com/jacket.jpg",
      description: "Classic denim jacket perfect for layering",
      link: "https://example.com/jacket",
      shop: "Fashion District"
    }
  ]
};

const MOCK_POSTS = [
  {
    id: "1",
    username: "fashionista",
    userAvatar: "https://example.com/avatar1.jpg",
    imageUrl: "https://example.com/fashion1.jpg",
    caption: "Styling the perfect casual weekend outfit with these amazing pieces! #fashion #style",
    link: "https://instagram.com/p/123"
  },
  {
    id: "2",
    username: "styleexpert",
    userAvatar: "https://example.com/avatar2.jpg",
    imageUrl: "https://example.com/fashion2.jpg",
    caption: "The essential summer wardrobe pieces you need this season ☀️ #summerstyle",
    link: "https://instagram.com/p/456"
  }
];

export const getMockResponse = (userMessage: Message): MockResponse => {
  // Check if it's a match request
  if (userMessage.content.toLowerCase().includes('match')) {
    return {
      content: "Here are some items that would match well with your selection:\n\n[PRODUCTS]\n\nI've also found some inspiring posts showing how to style these items:\n\n[POSTS]",
      products: MOCK_PRODUCTS.matching,
      posts: MOCK_POSTS.slice(0, 1)
    };
  }

  // Check if it's a similar items request
  if (userMessage.content.toLowerCase().includes('similar')) {
    return {
      content: "I found these similar items that match your style:\n\n[PRODUCTS]",
      products: MOCK_PRODUCTS.similar
    };
  }

  // Default response for other messages
  return {
    content: "Based on your style preferences, I've found some great items and trending posts that might interest you!\n\n[PRODUCTS]\n\nThese items are trending right now and would complement your style perfectly. I've also found some inspiring social media posts showing how to style similar pieces:\n\n[POSTS]\n\nLet me know if you'd like more specific recommendations or have any questions about the items!",
    products: MOCK_PRODUCTS.general,
    posts: MOCK_POSTS
  };
};

export const createMockBotMessage = (userMessage: Message): Message => {
  const mockResponse = getMockResponse(userMessage);
  
  return {
    id: uuidv4(),
    role: "assistant",
    content: mockResponse.content,
    timestamp: new Date(),
    products: mockResponse.products,
    posts: mockResponse.posts
  };
}; 