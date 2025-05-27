import { useState, useRef } from "react";
import { v4 as uuidv4 } from "uuid";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ChatMessage } from "@/components/chat/ChatMessage";
import type { Message } from "@/types/chat";
import { ImagePlus, Send, ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function ChatPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [selectedImages, setSelectedImages] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files) return;

    const newImages: string[] = [];
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        if (e.target?.result) {
          newImages.push(e.target.result as string);
          setSelectedImages([...selectedImages, ...newImages]);
        }
      };
      reader.readAsDataURL(file);
    });
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

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSelectedImages([]);
    setIsLoading(true);
    scrollToBottom();

    // TODO: Implement actual API call here
    // Mock response for now
    setTimeout(() => {
      const assistantMessage: Message = {
        id: uuidv4(),
        role: "assistant",
        content: "Here are some fashion recommendations based on your style:",
        timestamp: new Date(),
        products: [
          {
            name: "Classic White Sneakers",
            price: "$89.99",
            imageUrl: "https://example.com/sneakers.jpg",
            description: "Versatile white sneakers that go with everything",
            link: "https://example.com/product"
          }
        ]
      };
      setMessages((prev) => [...prev, assistantMessage]);
      setIsLoading(false);
      scrollToBottom();
    }, 1000);
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
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
        <h1 className="text-xl font-semibold text-gray-900">Fashion Assistant</h1>
      </div>

      {/* Main chat container */}
      <div className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full py-16 px-4">
                <h2 className="text-2xl font-semibold text-gray-900 mb-2">
                  Welcome to Fashion Assistant
                </h2>
                <p className="text-gray-600 text-center mb-8 max-w-md">
                  Upload images of your style or items you're interested in, and I'll help you with fashion recommendations.
                </p>
              </div>
            ) : (
              <div className="py-8 px-4">
                {messages.map((message) => (
                  <div key={message.id} className="mb-8">
                    <ChatMessage message={message} />
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
            <div className="flex gap-2 mb-4 overflow-x-auto pb-2">
              {selectedImages.map((image, index) => (
                <img
                  key={index}
                  src={image}
                  alt={`Selected ${index + 1}`}
                  className="w-20 h-20 object-cover rounded shadow-md"
                />
              ))}
            </div>
          )}
          
          <div className="flex gap-2 items-center">
            <input
              type="file"
              ref={fileInputRef}
              className="hidden"
              accept="image/*"
              multiple
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
                placeholder="Type your message..."
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
  );
} 