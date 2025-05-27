import { cn } from "@/lib/utils";
import type { Message, Product } from "@/types/chat";
import { Card } from "@/components/ui/card";
import { User, Bot } from "lucide-react";

interface ChatMessageProps {
  message: Message;
}

function ProductCard({ product }: { product: Product }) {
  return (
    <Card className="p-4 my-2 border border-gray-200 shadow-md hover:shadow-lg transition-shadow">
      <div className="flex gap-4">
        <img src={product.imageUrl} alt={product.name} className="w-24 h-24 object-cover rounded shadow" />
        <div>
          <h4 className="font-semibold text-gray-900">{product.name}</h4>
          <p className="text-sm text-gray-600">{product.description}</p>
          <p className="font-medium mt-1 text-blue-600">{product.price}</p>
          {product.link && (
            <a
              href={product.link}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:text-blue-800 hover:underline"
            >
              View Product
            </a>
          )}
        </div>
      </div>
    </Card>
  );
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={cn(
      "group relative",
      isUser ? "bg-white" : "bg-gray-50"
    )}>
      <div className="absolute left-4 top-4">
        {isUser ? (
          <div className="h-8 w-8 rounded-full bg-gray-300 flex items-center justify-center">
            <User className="h-5 w-5 text-gray-600" />
          </div>
        ) : (
          <div className="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center">
            <Bot className="h-5 w-5 text-white" />
          </div>
        )}
      </div>
      
      <div className="px-16 py-6">
        <div className="prose prose-sm max-w-none">
          <p className="text-gray-900">{message.content}</p>
        </div>

        {message.images && message.images.length > 0 && (
          <div className="mt-4 grid grid-cols-2 gap-4 max-w-lg">
            {message.images.map((image, index) => (
              <img
                key={index}
                src={image}
                alt={`Image ${index + 1}`}
                className="rounded-lg w-full h-48 object-cover shadow-md"
              />
            ))}
          </div>
        )}

        {message.products && message.products.length > 0 && (
          <div className="mt-4 space-y-4">
            {message.products.map((product, index) => (
              <ProductCard key={index} product={product} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
} 