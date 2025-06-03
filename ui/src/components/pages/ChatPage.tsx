import { useState, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatMessage } from "@/components/chat/ChatMessage";
import type { Message, Product, SocialMediaPost } from "@/types/chat";
import { ImagePlus, Send, ArrowLeft, X, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { CHAT_MODE, MOCK_DELAYS, DEMO_MODE } from "@/config/chat";
import { createMockBotMessage } from "@/mocks/chatResponses";
import { sendChatMessage } from "@/services/chatService";
import { toast } from "@/components/ui/use-toast";

export default function ChatPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [sidebarProducts, setSidebarProducts] = useState<Product[]>([]);
  const [sidebarPosts, setSidebarPosts] = useState<SocialMediaPost[]>([]);
  const [sidebarType, setSidebarType] = useState<'products' | 'posts'>('products');

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    const file = files[0]; // Only take the first file
    const reader = new FileReader();
    reader.onload = (e) => {
      if (e.target?.result) {
        setSelectedImages([e.target.result as string]);
      }
    };
    reader.readAsDataURL(file);
    
    // Reset the file input value to allow the same file to be selected again
    event.target.value = '';
  };

  const handleMoreProducts = (products: Product[]) => {
    setSidebarType('products');
    setSidebarProducts(products);
    setIsSidebarOpen(true);
  };

  const handleMorePosts = (posts: SocialMediaPost[]) => {
    setSidebarType('posts');
    setSidebarPosts(posts);
    setIsSidebarOpen(true);
  };

  const handleBotResponse = async (userMessage: Message) => {
    try {
      let botMessage: Message;
      
      if (CHAT_MODE === 'mock') {
        // Use mock data with delay
        await new Promise(resolve => setTimeout(resolve, MOCK_DELAYS.BOT_RESPONSE));
        botMessage = createMockBotMessage(userMessage);
      } else {
        // Use real API
        const imageBase64 = userMessage.images?.[0] || "";
        
        // Validate image size if present
        if (imageBase64) {
          const sizeInBytes = Math.ceil((imageBase64.length * 3) / 4);
          const sizeInMB = sizeInBytes / (1024 * 1024);
          if (sizeInMB > 15) {  // Leave 1MB buffer from server's 16MB limit
            throw new Error("Image size too large. Please use an image under 15MB.");
          }
        }

        // First try health check
        try {
          console.log("Testing server connection...");
          const healthCheck = await fetch('http://localhost:8000/api/health');
          if (!healthCheck.ok) {
            throw new Error('Server health check failed');
          }
          console.log("Server is healthy");
        } catch (error) {
          console.error("Health check failed:", error);
          throw new Error('Cannot connect to server. Please ensure the server is running.');
        }

        const payload = {
          query_text: userMessage.content || "",
          image_base64: imageBase64
        };
        console.log("Sending request with payload length:", JSON.stringify(payload).length);

        const response = await fetch('http://localhost:8000/api/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(payload)
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.error || 'Server error');
        }

        const data = await response.json();
        
        if (data.error) {
          throw new Error(data.error);
        }

        botMessage = {
          id: uuidv4(),
          role: "assistant",
          content: data.text,
          timestamp: new Date(),
          products: data.products?.map((p: any) => ({
            ...p,
            shop: p.brand,  // Map brand to shop for frontend display
            link: null  // Add any product link if available
          }))
        };
      }

      setMessages(prev => [...prev, botMessage]);
      setIsLoading(false);
      scrollToBottom();
    } catch (error) {
      console.error('Error getting bot response:', error);
      toast({
        title: "Error",
        description: error instanceof Error ? error.message : "Failed to get response from the assistant. Please try again.",
        variant: "destructive"
      });
      setIsLoading(false);
    }
  };

  const handleSend = async () => {
    if (!input.trim() && selectedImages.length === 0) return;

    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content: input,
      timestamp: new Date(),
      images: selectedImages,
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setSelectedImages([]);
    setIsLoading(true);
    scrollToBottom();

    await handleBotResponse(userMessage);
  };

  const handleMatchThis = async (product: Product) => {
    const message = `Can you help me find outfits and items that would match with this ${product.name}?`;
    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content: message,
      timestamp: new Date(),
      products: [product]
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setIsSidebarOpen(false);
    scrollToBottom();

    await handleBotResponse(userMessage);
  };

  const handleSimilarItems = async (product: Product) => {
    const message = `Can you show me similar items to this ${product.name}?`;
    const userMessage: Message = {
      id: uuidv4(),
      role: "user",
      content: message,
      timestamp: new Date(),
      products: [product]
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setIsSidebarOpen(false);
    scrollToBottom();

    await handleBotResponse(userMessage);
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-white border-b border-gray-200 px-4 py-3 flex items-center">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigate("/")}
            className="mr-4"
          >
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-xl font-semibold text-gray-900">穿搭助理</h1>
        </div>

        {/* Main chat container */}
        <div className="flex-1 overflow-hidden">
          <div className="h-full overflow-y-auto">
            <div className="max-w-3xl mx-auto">
              {messages.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full py-16 px-4">
                  <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                    我是穿搭助理
                  </h2>
                  <p className="text-gray-600 text-center mb-8 max-w-md">
                    上傳你想搭配的衣服，輸入條件，我會幫你找到適合的商品。
                  </p>
                </div>
              ) : (
                <div className="py-8 px-4">
                  {messages.map((message) => (
                    <div key={message.id} className="mb-8">
                      <ChatMessage 
                        message={message} 
                        onMoreProducts={handleMoreProducts}
                        onMorePosts={handleMorePosts}
                        onSendMessage={(content: string, product: Product) => {
                          const message = `${content}`;
                          const userMessage: Message = {
                            id: uuidv4(),
                            role: "user",
                            content: message,
                            timestamp: new Date(),
                            products: [product]
                          };

                          setMessages(prev => [...prev, userMessage]);
                          setIsLoading(true);
                          scrollToBottom();

                          handleBotResponse(userMessage);
                        }}
                      />
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Input area */}
        <div className="border-t border-gray-200 bg-white">
          <div className="max-w-3xl mx-auto p-4">
            {selectedImages.length > 0 && (
              <div className="mb-4 flex justify-end">
                <div className="relative">
                  <img
                    src={selectedImages[0]}
                    alt="Selected"
                    className="w-20 h-20 object-cover rounded shadow-md"
                  />
                  <Button
                    variant="ghost"
                    size="icon"
                    className="absolute -top-2 -right-2 h-6 w-6 rounded-full bg-gray-800/50 hover:bg-gray-800/75 text-white"
                    onClick={() => setSelectedImages([])}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
            
            <div className="flex gap-2 items-center">
              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept="image/*"
                onChange={handleFileSelect}
              />
              <Button
                variant="outline"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                className="border-gray-300 hover:bg-gray-100"
              >
                <ImagePlus className="h-5 w-5 text-gray-600" />
              </Button>
              <div className="flex-1 relative">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="幫我找500元以下的上衣..."
                  onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
                  className="pr-12 py-6 text-base border-gray-300 focus:border-blue-500 shadow-sm"
                />
                <Button 
                  onClick={handleSend} 
                  disabled={isLoading}
                  className="absolute right-2 top-1/2 -translate-y-1/2 bg-blue-600 text-white hover:bg-blue-700"
                >
                  <Send className="h-5 w-5" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className={`fixed inset-y-0 right-0 w-96 bg-white shadow-xl transform transition-transform duration-300 ease-in-out ${isSidebarOpen ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="h-full flex flex-col">
          <div className="p-4 border-b border-gray-200 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900">
              {sidebarType === 'products' ? 'More Products' : 'More Posts'}
            </h2>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setIsSidebarOpen(false)}
              className="hover:bg-gray-100"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
          <div className="flex-1 overflow-y-auto p-4">
            <div className="space-y-4">
              {sidebarType === 'products' ? (
                sidebarProducts.map((product, index) => (
                  <div
                    key={index}
                    className="p-4 border border-gray-200 rounded-lg hover:shadow-md transition-shadow"
                  >
                    <div className="flex gap-4">
                      <img
                        src={product.imageUrl}
                        alt={product.name}
                        className="w-24 h-24 object-cover rounded"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <h3 className="font-semibold text-gray-900">{product.name}</h3>
                          <span className="text-sm text-gray-600">{product.shop}</span>
                        </div>
                        <p className="text-sm text-gray-600">{product.description}</p>
                        <div className="flex items-center justify-between mt-2">
                          <p className="font-medium text-blue-600">NT. {product.price}</p>
                          {!DEMO_MODE && product.link && (
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
                        {!DEMO_MODE && (
                          <div className="flex gap-2 mt-3 pt-3 border-t border-gray-100">
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1 text-sm"
                              onClick={() => handleMatchThis(product)}
                            >
                              Match This
                            </Button>
                            <Button
                              variant="outline"
                              size="sm"
                              className="flex-1 text-sm"
                              onClick={() => handleSimilarItems(product)}
                            >
                              Similar Items
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                sidebarPosts.map((post) => (
                  <div
                    key={post.id}
                    className="border border-gray-200 rounded-lg overflow-hidden hover:shadow-md transition-shadow"
                  >
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
                      <p className="text-sm text-gray-900">{post.caption}</p>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
} 