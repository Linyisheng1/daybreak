export const landingSeo = {
  siteUrl: "https://daybreak.local/",
  siteName: "破晓 Daybreak",
  title: "破晓 Daybreak - 安全评估工作台",
  description:
    "破晓是一个开源安全评估工作台，提供多智能体编排、工作项目取证记录、分布式Docker沙箱、受管出口和可回放时间线。",
  imagePath: "assets/z3r0-logo.png",
  imageAlt: "破晓 Daybreak logo",
  keywords: [
    "破晓",
    "Daybreak",
    "安全评估工作台",
    "多智能体安全平台",
    "授权渗透测试",
    "漏洞研究",
    "漏洞验证",
    "安全评估编排",
    "攻击路径分析",
    "攻击路径回放",
    "沙箱安全工具",
    "分布式Docker沙箱",
    "受管出口",
    "代理出口",
    "取证记录",
    "资产关系图谱",
    "工作项目记录",
    "代码审计自动化",
    "源代码安全审计",
    "依赖审查",
    "安全发现管理",
    "智能体编排",
    "逆向工程自动化",
    "密码学审查",
  ],
};

export const structuredData = [
  {
    "@context": "https://schema.org",
    "@type": "SoftwareApplication",
    name: landingSeo.siteName,
    applicationCategory: "SecurityApplication",
    operatingSystem: "Linux, Docker",
    url: landingSeo.siteUrl,
    image: new URL(landingSeo.imagePath, landingSeo.siteUrl).toString(),
    description: landingSeo.description,
    softwareRequirements: "Docker Engine, Docker Compose, PostgreSQL, model provider credentials",
    offers: {
      "@type": "Offer",
      price: "0",
      priceCurrency: "USD",
    },
    sameAs: ["https://github.com/Linyisheng1/daybreak"],
  },
  {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: [
      {
        "@type": "Question",
        name: "什么是破晓?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "破晓是一个开源安全评估工作台，用于授权渗透测试、漏洞发现、代码审计和安全研究。",
        },
      },
      {
        "@type": "Question",
        name: "破晓面向哪些用户?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "破晓面向授权红队、渗透测试人员、漏洞研究人员、内部安全团队、代码审计人员、逆向工程师、密码学审查人员和受控研究环境。",
        },
      },
      {
        "@type": "Question",
        name: "破晓如何运行安全工具?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "破晓将智能体工具和手动审查工作流绑定到受控Docker沙箱容器，支持命令执行、文件访问、Shell访问、浏览器工作流和noVNC审查。",
        },
      },
      {
        "@type": "Question",
        name: "哪些环境应使用破晓?",
        acceptedAnswer: {
          "@type": "Answer",
          text: "破晓应仅在合法且明确授权的、受信任的和隔离的环境中使用，其中Docker访问、模型凭据、终端访问和沙箱容器可以作为高特权资产进行管理。",
        },
      },
    ],
  },
  {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      {
        "@type": "ListItem",
        position: 1,
        name: "破晓",
        item: landingSeo.siteUrl,
      },
    ],
  },
];

export function getRobotsTxt() {
  return [
    "User-agent: *",
    "Allow: /",
    "",
    `Sitemap: ${new URL("sitemap.xml", landingSeo.siteUrl).toString()}`,
    "",
  ].join("\n");
}

export function getSitemapXml() {
  return [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    "  <url>",
    `    <loc>${landingSeo.siteUrl}</loc>`,
    "    <changefreq>weekly</changefreq>",
    "    <priority>1.0</priority>",
    "  </url>",
    "</urlset>",
    "",
  ].join("\n");
}

export function getWebManifest(iconSrc: string) {
  return JSON.stringify(
    {
      name: "破晓 Daybreak",
      short_name: "破晓",
      description: landingSeo.description,
      start_url: "/",
      display: "standalone",
      background_color: "#f5f7fa",
      theme_color: "#2563eb",
      icons: [
        {
          src: iconSrc,
          sizes: "1000x1000",
          type: "image/png",
          purpose: "any",
        },
      ],
    },
    null,
    2,
  );
}
