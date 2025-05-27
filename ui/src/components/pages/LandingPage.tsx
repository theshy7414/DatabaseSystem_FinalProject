import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { MessageSquare, Image, ShoppingBag, Zap } from "lucide-react";

export default function LandingPage() {
  const navigate = useNavigate();

  const features = [
    {
      icon: <MessageSquare className="h-8 w-8" />,
      title: "AI-Powered Chat",
      description: "Get personalized fashion advice through natural conversation"
    },
    {
      icon: <Image className="h-8 w-8" />,
      title: "Image Upload",
      description: "Share your style or items you're interested in"
    },
    {
      icon: <ShoppingBag className="h-8 w-8" />,
      title: "Product Recommendations",
      description: "Receive curated product suggestions based on your preferences"
    },
    {
      icon: <Zap className="h-8 w-8" />,
      title: "Instant Styling Tips",
      description: "Get real-time fashion advice and outfit combinations"
    }
  ];

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold mb-4 text-gray-900">
            Your Personal Fashion Assistant
          </h1>
          <p className="text-xl text-gray-600 mb-8">
            Get personalized fashion recommendations and style advice powered by AI
          </p>
          <Button
            size="lg"
            onClick={() => navigate("/chat")}
            className="bg-blue-600 text-white hover:bg-blue-700 px-8 py-6 text-lg font-semibold shadow-lg"
          >
            Start Chatting
          </Button>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
          {features.map((feature, index) => (
            <div
              key={index}
              className="p-6 bg-white rounded-xl shadow-lg hover:shadow-xl transition-shadow border border-gray-200"
            >
              <div className="mb-4 text-blue-600">{feature.icon}</div>
              <h3 className="text-xl font-semibold mb-2 text-gray-900">{feature.title}</h3>
              <p className="text-gray-600">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
} 