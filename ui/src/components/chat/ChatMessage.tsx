import { cn } from "@/lib/utils";
import type { Message, Product, SocialMediaPost } from "@/types/chat";
import { Card } from "@/components/ui/card";
import { User, Bot, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ChatMessageProps {
  message: Message;
  onMoreProducts?: (products: Product[]) => void;
  onMorePosts?: (posts: SocialMediaPost[]) => void;
  onSendMessage?: (message: string, product: Product) => void;
}

interface ProductCardProps {
  product: Product;
  showActions?: boolean;
  onMatchThis?: (product: Product) => void;
  onSimilarItems?: (product: Product) => void;
}

function ProductCard({ product, showActions = true, onMatchThis, onSimilarItems }: ProductCardProps) {
  return (
    <Card className="p-4 my-2 border border-gray-200 shadow-md hover:shadow-lg transition-shadow">
      <div className="flex gap-4">
        <img src={product.imageUrl} alt={product.name} className="w-24 h-24 object-cover rounded shadow" />
        <div className="flex-1">
          <div className="flex items-center justify-between mb-1">
            <h4 className="font-semibold text-gray-900">{product.name}</h4>
            <span className="text-sm text-gray-600">{product.shop}</span>
          </div>
          <p className="text-sm text-gray-600">{product.description}</p>
          <div className="flex items-center justify-between mt-2">
            <p className="font-medium text-blue-600">{product.price}</p>
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
          {showActions && onMatchThis && onSimilarItems && (
            <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
              <Button
                variant="outline"
                size="sm"
                className="flex-1 text-sm"
                onClick={() => onMatchThis(product)}
              >
                Match This
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="flex-1 text-sm"
                onClick={() => onSimilarItems(product)}
              >
                Similar Items
              </Button>
            </div>
          )}
        </div>
      </div>
    </Card>
  );
}

function SocialMediaPostCard({ post }: { post: SocialMediaPost }) {
  return (
    <Card className="overflow-hidden border border-gray-200 shadow-sm hover:shadow-md transition-shadow">
      <div className="p-3 flex items-center gap-3 border-b border-gray-100">
        <img 
          src={post.userAvatar} 
          alt={post.username}
          className="w-8 h-8 rounded-full object-cover"
        />
        <span className="font-medium text-gray-900">{post.username}</span>
      </div>
      <div className="aspect-square relative">
        <img 
          src={post.imageUrl} 
          alt="Post content"
          className="w-full h-full object-cover"
        />
        <a
          href={post.link}
          target="_blank"
          rel="noopener noreferrer"
          className="absolute bottom-3 right-3 bg-black/70 text-white p-2 rounded-full hover:bg-black/90 transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
        </a>
      </div>
      <div className="p-3">
        <p className="text-sm text-gray-900 line-clamp-2">{post.caption}</p>
      </div>
    </Card>
  );
}

export function ChatMessage({ message, onMoreProducts, onMorePosts, onSendMessage }: ChatMessageProps) {
  const isUser = message.role === "user";

  // Split content by special markers for products and posts sections
  const parts = message.content.split(/(\[PRODUCTS\]|\[POSTS\])/g).filter(Boolean);
  const productIndex = parts.indexOf('[PRODUCTS]');
  const postIndex = parts.indexOf('[POSTS]');

  const hasOnlyText = !message.images?.length && !message.products?.length && !message.posts?.length;

  const handleMatchThis = (product: Product) => {
    if (onSendMessage) {
      onSendMessage(
        `Can you help me find outfits and items that would match with this ${product.name}?`,
        product
      );
    }
  };

  const handleSimilarItems = (product: Product) => {
    if (onSendMessage) {
      onSendMessage(
        `Can you show me similar items to this ${product.name}?`,
        product
      );
    }
  };

  return (
    <div className={cn(
      "group relative flex",
      isUser ? "justify-end" : "justify-start"
    )}>
      <div className={cn(
        "relative max-w-[80%]",
        isUser ? "order-1 mr-4" : "order-2 ml-4"
      )}>
        <div className={cn(
          "px-6 py-4 rounded-3xl",
          isUser ? "bg-blue-600 text-white" : "bg-white border border-gray-200",
          isUser ? "rounded-br-lg" : "rounded-bl-lg",
          hasOnlyText ? "pb-3" : "pb-4"
        )}>
          {/* Initial text */}
          <div className={cn(
            "prose prose-sm max-w-none",
            !hasOnlyText && "mb-4"
          )}>
            <p className={cn(
              isUser ? "text-white" : "text-gray-900"
            )}>{isUser ? message.content : (productIndex > 0 ? parts[0] : message.content)}</p>
          </div>

          {/* User uploaded images */}
          {message.images && message.images.length > 0 && (
            <div className={cn(
              "mt-4",
              isUser && "flex justify-end"
            )}>
              <img
                src={message.images[0]}
                alt="Uploaded image"
                className="rounded-lg w-64 h-64 object-cover shadow-md"
              />
            </div>
          )}

          {/* Products section */}
          {message.products && message.products.length > 0 && (
            <div className="mt-4">
              <div className="space-y-4">
                {message.products.slice(0, 2).map((product, index) => (
                  <ProductCard 
                    key={index} 
                    product={product}
                    showActions={!isUser}
                    onMatchThis={!isUser ? handleMatchThis : undefined}
                    onSimilarItems={!isUser ? handleSimilarItems : undefined}
                  />
                ))}
              </div>
              {!isUser && message.products.length > 2 && onMoreProducts && (
                <Button
                  variant="outline"
                  className="mt-4 bg-white text-blue-600 hover:text-blue-700 border-blue-200 hover:bg-blue-50 w-full"
                  onClick={() => onMoreProducts(message.products || [])}
                >
                  View More Products
                </Button>
              )}
            </div>
          )}

          {/* Text between products and posts */}
          {!isUser && postIndex > productIndex + 1 && (
            <div className="prose prose-sm max-w-none my-4">
              <p className={cn(
                isUser ? "text-white" : "text-gray-900"
              )}>{parts[productIndex + 1]}</p>
            </div>
          )}

          {/* Posts section */}
          {!isUser && message.posts && message.posts.length > 0 && (
            <div className="mt-4">
              <div className="grid grid-cols-2 gap-4">
                {message.posts.slice(0, 2).map((post) => (
                  <SocialMediaPostCard key={post.id} post={post} />
                ))}
              </div>
              {message.posts.length > 2 && onMorePosts && (
                <Button
                  variant="outline"
                  className="mt-4 bg-white text-blue-600 hover:text-blue-700 border-blue-200 hover:bg-blue-50 w-full"
                  onClick={() => onMorePosts(message.posts || [])}
                >
                  View More Posts
                </Button>
              )}
            </div>
          )}

          {/* Final text */}
          {!isUser && parts.length > postIndex + 1 && (
            <div className="prose prose-sm max-w-none mt-4">
              <p className={cn(
                isUser ? "text-white" : "text-gray-900"
              )}>{parts[parts.length - 1]}</p>
            </div>
          )}
        </div>
      </div>

      <div className={cn(
        "h-8 w-8 rounded-full flex items-center justify-center self-end mb-2",
        isUser ? "order-2 bg-blue-700" : "order-1 bg-gray-200",
        isUser ? "ml-0" : "mr-0"
      )}>
        {isUser ? (
          <User className="h-5 w-5 text-white" />
        ) : (
          <Bot className="h-5 w-5 text-gray-600" />
        )}
      </div>
    </div>
  );
} 