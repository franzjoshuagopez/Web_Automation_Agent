import { useEffect, useState } from "react";
import Layout from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Search, ChevronLeft, ChevronRight, Code } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";

interface DOMElement {
  index: number;
  tag: string;
  text: string;
  selectorType: string;
  selector: string;
  sourceUrl: string;
  [key: string]: any;
}

/* const mockElements: DOMElement[] = Array.from({ length: 50 }, (_, i) => ({
  index: i,
  tag: ["button", "input", "div", "a", "span"][Math.floor(Math.random() * 5)],
  text: `Element ${i}: Sample text content`,
  selectorType: ["id", "class", "xpath"][Math.floor(Math.random() * 3)],
  selector: `#element-${i}`,
  attributes: {
    id: `element-${i}`,
    class: "sample-class",
    role: "button",
  },
})); */

export default function Elements() {
  const [elements, setElements] = useState<DOMElement[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterTag, setFilterTag] = useState<string>("all");
  const [currentPage, setCurrentPage] = useState(1);
  const itemsPerPage = 10;

  useEffect(() => {
    const fetchElements = async () => {
      try {
        const res = await fetch("http://localhost:8000/api/elements");
        const data = await res.json();
        const mapped = Object.entries(data).flatMap(
          ([url, elements]: [string, any[]]) =>
            elements.map((el, i) => ({
              index: i,
              tag: el.tag,
              text: el.text,
              selectorType: el.selector_type,
              selector: el.selector,
              sourceUrl: url,
              ...el,
            }))
        );

        setElements(mapped);

      } catch (error) {
        console.error("Failed to fetch elements: ", error)
      }
    };

    fetchElements();

  }, []);

  const filteredElements = elements.filter((el) => {
    const matchesSearch =
      searchQuery === "" ||
      el.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
      el.selector.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTag = filterTag === "all" || el.tag === filterTag;
    return matchesSearch && matchesTag;
  });

  const totalPages = Math.ceil(filteredElements.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const paginatedElements = filteredElements.slice(
    startIndex,
    startIndex + itemsPerPage
  );

  return (
    <Layout>
      {/* Header */}
      <div className="border-b border-border bg-card px-8 py-6">
        <h1 className="text-3xl font-bold mb-2">Element Viewer</h1>
        <p className="text-muted-foreground">
          Inspect and query DOM elements from automation runs
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-7xl mx-auto space-y-6">
          {/* Filters */}
          <Card className="p-6">
            <div className="flex gap-4">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <Input
                  placeholder="Search by text or selector..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              <Select value={filterTag} onValueChange={setFilterTag}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by tag" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Tags</SelectItem>
                  <SelectItem value="button">Button</SelectItem>
                  <SelectItem value="input">Input</SelectItem>
                  <SelectItem value="div">Div</SelectItem>
                  <SelectItem value="a">Link</SelectItem>
                  <SelectItem value="span">Span</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </Card>

          {/* Elements List */}
          <div className="space-y-3">
            {paginatedElements.map((element) => (
              <Card key={element.index} className="hover:shadow-md transition-smooth">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-3">
                        <span className="text-xs font-mono bg-muted px-2 py-1 rounded">
                          {element.index}
                        </span>
                        <span className="text-sm font-medium bg-primary/10 text-primary px-2 py-1 rounded">
                          &lt;{element.tag}&gt;
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {element.selectorType}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground break-all">{element.sourceUrl}</p>
                      <p className="text-sm">{element.text}</p>
                      <code className="text-xs font-mono bg-muted px-2 py-1 rounded block break-all">
                        {element.selector}
                      </code>
                    </div>
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="outline" size="sm">
                          <Code className="h-4 w-4 mr-2" />
                          Details
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl">
                        <DialogHeader>
                          <DialogTitle>Element Details</DialogTitle>
                          <DialogDescription>
                            Complete information about element #{element.index}
                          </DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4">
                          <div>
                            <h4 className="font-medium mb-2">Basic Info</h4>
                            <div className="grid grid-cols-2 gap-4 text-sm">
                              <div>
                                <span className="text-muted-foreground">
                                  Index:
                                </span>{" "}
                                {element.index}
                              </div>
                              <div>
                                <span className="text-muted-foreground">Tag:</span>{" "}
                                {element.tag}
                              </div>
                              <div>
                                <span className="text-muted-foreground">
                                  Selector Type:
                                </span>{" "}
                                {element.selectorType}
                              </div>
                            </div>
                          </div>
                          <div>
                            <h4 className="font-medium mb-2">Selector</h4>
                            <code className="block p-3 bg-console-bg text-console-text rounded font-mono text-sm">
                              {element.selector}
                            </code>
                          </div>
                          <div>
                            <h4 className="font-medium mb-2">Attributes</h4>
                            <code className="block p-3 bg-console-bg text-console-text rounded font-mono text-sm">
                              {JSON.stringify(element.attributes, null, 2)}
                            </code>
                          </div>
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Showing {startIndex + 1} to{" "}
              {Math.min(startIndex + itemsPerPage, filteredElements.length)} of{" "}
              {filteredElements.length} elements
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <div className="flex items-center gap-2">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map(
                  (page) => (
                    <Button
                      key={page}
                      variant={currentPage === page ? "default" : "outline"}
                      size="sm"
                      onClick={() => setCurrentPage(page)}
                      className={
                        currentPage === page ? "gradient-primary" : ""
                      }
                    >
                      {page}
                    </Button>
                  )
                )}
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setCurrentPage((p) => Math.min(totalPages, p + 1))
                }
                disabled={currentPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}
