export type BillingProduct = {
  sku: string;
  name: string;
  eyebrow: string;
  price: string;
  suffix?: string;
  description: string;
  featured?: boolean;
};

export const billingProducts: BillingProduct[] = [
  {
    sku: "free_first_generation",
    name: "Try Vastu AI",
    eyebrow: "Free",
    price: "₹0",
    description: "Your first successful plan generation is free.",
  },
  {
    sku: "project_single",
    name: "Single Project",
    eyebrow: "Pay once",
    price: "₹399",
    description:
      "One permanent paid project with repeat edits and generations.",
  },
  {
    sku: "project_pack_10",
    name: "10 Project Pack",
    eyebrow: "Studio pack",
    price: "₹3,399",
    description: "Ten permanent project entitlements for client work.",
  },
  {
    sku: "pro_monthly",
    name: "Pro Monthly",
    eyebrow: "Most flexible",
    price: "₹2,499",
    suffix: "/month",
    description: "Subscription access for active professional work.",
    featured: true,
  },
  {
    sku: "pro_yearly",
    name: "Pro Yearly",
    eyebrow: "Best value",
    price: "₹24,999",
    suffix: "/year",
    description: "Save ₹4,989 compared with twelve monthly payments.",
  },
];
