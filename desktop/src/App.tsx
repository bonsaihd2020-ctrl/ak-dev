import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  Box, Flex, VStack, HStack, Text, Input, Button, IconButton, Badge,
  useColorModeValue, Spinner, Tooltip, Tabs, TabList, TabPanels, Tab, TabPanel,
  Select, Switch, Divider, useToast, Modal, ModalOverlay, ModalContent, ModalHeader,
  ModalBody, ModalCloseButton, useDisclosure, Code, Textarea, SimpleGrid,
} from "@chakra-ui/react";
import {
  FiSend, FiPause, FiPlay, FiSquare, FiSettings, FiFolder, FiMonitor,
  FiTerminal, FiCpu, FiDatabase, FiZap, FiCheckCircle, FiAlertCircle,
  FiSearch, FiDownload, FiUser, FiKey, FiGlobe, FiRefreshCw,
} from "react-icons/fi";
import * as api from "./api";

declare global {
  interface Window {
    electronAPI: {
      selectFolder: () => Promise<string | null>;
      selectFile: () => Promise<string | null>;
      minimize: () => void;
      maximize: () => void;
      close: () => void;
    };
  }
}

interface AgentEvent {
  type?: string;
  agent?: string;
  content?: string;
  tool?: string;
  args?: any;
  result?: any;
  event?: string;
  message?: string;
  thought?: string;
}

interface Provider {
  id: string;
  name: string;
  base_url: string;
  auth_type: string;
  supports_browser_login: boolean;
  has_key: boolean;
  selected_model?: string;
}

function TitleBar() {
  return (
    <HStack bg="#08080d" px={4} py={2} justify="space-between" userSelect="none">
      <HStack>
        <FiCpu color="#0070e0" size={18} />
        <Text fontWeight={700} fontSize="sm" bgGradient="linear(to-r, blue.400, cyan.400)" bgClip="text">
          Devin Clone
        </Text>
      </HStack>
      <HStack spacing={2}>
        <IconButton aria-label="Minimize" size="xs" variant="ghost" icon={<Box w={3} h="1px" bg="white" />} onClick={() => window.electronAPI?.minimize()} />
        <IconButton aria-label="Maximize" size="xs" variant="ghost" icon={<Box w={3} h={3} border="1px solid white" borderRadius={1} />} onClick={() => window.electronAPI?.maximize()} />
        <IconButton aria-label="Close" size="xs" variant="ghost" icon={<Text fontSize="xs">×</Text>} onClick={() => window.electronAPI?.close()} />
      </HStack>
    </HStack>
  );
}

function AgentTimeline({ currentAgent, completedAgents }: { currentAgent: string; completedAgents: string[] }) {
  const agents = ["Plan", "Architect", "Code", "Review", "Test"];
  const agentColors: Record<string, string> = { Plan: "purple", Architect: "blue", Code: "green", Review: "orange", Test: "cyan" };

  return (
    <HStack spacing={1} px={4} py={2} bg="#0d0d14" borderBottom="1px solid #1e1e2e" overflowX="auto">
      {agents.map((a, i) => {
        const isActive = currentAgent.toLowerCase().includes(a.toLowerCase());
        const isDone = completedAgents.includes(a.toLowerCase());
        const color = agentColors[a];
        return (
          <HStack key={a} spacing={1}>
            <Badge
              colorScheme={isActive ? color : isDone ? "green" : "gray"}
              variant={isActive ? "solid" : isDone ? "subtle" : "outline"}
              px={2} py={1} borderRadius="md" fontSize="xs"
            >
              {isDone && <FiCheckCircle style={{ marginRight: 4 }} />}
              {a}
            </Badge>
            {i < agents.length - 1 && <Text color="gray.600" fontSize="xs">→</Text>}
          </HStack>
        );
      })}
    </HStack>
  );
}

function ChatPanel({
  messages, onSend, isRunning, onPause, onResume, onStop, currentAgent, completedAgents
}: {
  messages: AgentEvent[]; onSend: (msg: string) => void; isRunning: boolean;
  onPause: () => void; onResume: () => void; onStop: () => void;
  currentAgent: string; completedAgents: string[];
}) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    if (input.trim()) {
      onSend(input.trim());
      setInput("");
    }
  };

  const bg = useColorModeValue("white", "#0a0a0f");

  return (
    <Flex direction="column" h="100%" bg={bg}>
      <AgentTimeline currentAgent={currentAgent} completedAgents={completedAgents} />
      <Flex flex={1} overflowY="auto" p={4} direction="column" gap={3}>
        {messages.map((msg, i) => (
          <Box key={i}>
            {msg.event === "content" && (
              <HStack align="flex-start" spacing={3}>
                <Box bg="blue.600" borderRadius="full" p={2}><FiCpu size={14} /></Box>
                <Box bg="#12121a" borderRadius="lg" px={4} py={2} maxW="85%" border="1px solid #1e1e2e">
                  <Text fontSize="xs" color="blue.400" mb={1}>{msg.agent || "Agent"}</Text>
                  <Text fontSize="sm" whiteSpace="pre-wrap">{msg.content}</Text>
                </Box>
              </HStack>
            )}
            {msg.event === "tool_call" && (
              <HStack align="flex-start" spacing={3} ml={8}>
                <FiZap size={14} color="yellow.400" />
                <Box bg="#1a1520" borderRadius="lg" px={3} py={2} border="1px solid #2d2540">
                  <Text fontSize="xs" color="yellow.400">{msg.tool}</Text>
                  {msg.args && <Code fontSize="xs" display="block" mt={1} p={2} bg="transparent" whiteSpace="pre-wrap">{JSON.stringify(msg.args, null, 2)}</Code>}
                </Box>
              </HStack>
            )}
            {msg.event === "tool_result" && (
              <HStack align="flex-start" spacing={3} ml={8}>
                <FiCheckCircle size={14} color={msg.result?.success ? "green.400" : "red.400"} />
                <Box bg="#0f1a0f" borderRadius="lg" px={3} py={2} border="1px solid #1a2e1a" maxW="85%">
                  <Text fontSize="xs" color={msg.result?.success ? "green.400" : "red.400"}>Result: {msg.tool}</Text>
                  <Code fontSize="xs" display="block" mt={1} p={2} bg="transparent" whiteSpace="pre-wrap" maxH="200px" overflowY="auto">
                    {JSON.stringify(msg.result, null, 2)}
                  </Code>
                </Box>
              </HStack>
            )}
            {msg.event === "error" && (
              <Box ml={8} bg="#1a0f0f" borderRadius="lg" px={3} py={2} border="1px solid #2e1a1a">
                <Text fontSize="sm" color="red.400">{msg.message}</Text>
              </Box>
            )}
            {msg.event === "user_message" && (
              <HStack align="flex-start" spacing={3} justify="flex-end">
                <Box bg="blue.600" borderRadius="lg" px={4} py={2} maxW="85%">
                  <Text fontSize="sm" whiteSpace="pre-wrap">{msg.content}</Text>
                </Box>
                <Box bg="blue.800" borderRadius="full" p={2}><FiUser size={14} /></Box>
              </HStack>
            )}
            {msg.event === "agent_start" && msg.agent && (
              <HStack spacing={2} ml={2}>
                <Badge colorScheme="purple" fontSize="xs">{msg.agent}</Badge>
                <Text fontSize="xs" color="gray.500">starting...</Text>
              </HStack>
            )}
            {msg.event === "monologue" && msg.agent && (
              <HStack align="flex-start" spacing={3} ml={4}>
                <Box bg="purple.900" borderRadius="full" p={1.5}><FiCpu size={10} color="purple.300" /></Box>
                <Box bg="#15101f" borderRadius="lg" px={3} py={2} maxW="80%" border="1px solid #2d2540" borderStyle="dashed">
                  <Text fontSize="xs" color="purple.300" mb={1} fontStyle="italic">{msg.agent} thinking...</Text>
                  <Text fontSize="xs" color="gray.400" whiteSpace="pre-wrap">{msg.thought || msg.content}</Text>
                </Box>
              </HStack>
            )}
            {msg.event === "context_compressed" && (
              <HStack spacing={2} ml={4} py={1}>
                <FiRefreshCw size={12} color="cyan.400" />
                <Text fontSize="xs" color="cyan.400" fontStyle="italic">Context compressed for efficiency</Text>
              </HStack>
            )}
          </Box>
        ))}
        <div ref={messagesEndRef} />
      </Flex>

      <HStack p={3} borderTop="1px solid #1e1e2e" bg="#0d0d14">
        <Input
          value={input} onChange={(e) => setInput(e.target.value)}
          placeholder="Describe your task..."
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
          bg="#12121a" border="1px solid #1e1e2e" _focus={{ borderColor: "blue.500" }}
          size="md" flex={1}
        />
        {isRunning ? (
          <HStack>
            <Tooltip label="Pause"><IconButton aria-label="Pause" icon={<FiPause />} onClick={onPause} colorScheme="yellow" size="md" /></Tooltip>
            <Tooltip label="Stop"><IconButton aria-label="Stop" icon={<FiSquare />} onClick={onStop} colorScheme="red" size="md" /></Tooltip>
          </HStack>
        ) : (
          <Tooltip label="Send"><IconButton aria-label="Send" icon={<FiSend />} onClick={handleSend} colorScheme="blue" size="md" /></Tooltip>
        )}
      </HStack>
    </Flex>
  );
}

function WorkspacePanel() {
  const [status, setStatus] = useState<any>(null);
  const [tree, setTree] = useState<any>(null);

  const refresh = async () => {
    setStatus(await api.getWorkspaceStatus());
    if (status?.connected) setTree(await api.getWorkspaceTree());
  };

  useEffect(() => { refresh(); }, []);

  const handleConnect = async () => {
    const path = await window.electronAPI?.selectFolder();
    if (path) {
      await api.connectWorkspace(path);
      refresh();
    }
  };

  return (
    <VStack align="stretch" h="100%" p={3} spacing={3}>
      <HStack justify="space-between">
        <Text fontSize="sm" fontWeight={600}>Workspace</Text>
        <Button size="xs" leftIcon={<FiFolder />} onClick={handleConnect} colorScheme="blue" variant="ghost">Connect</Button>
      </HStack>
      {status?.connected ? (
        <Box>
          <Text fontSize="xs" color="gray.400" mb={2}>{status.root}</Text>
          {tree?.tree && <TreeView node={tree.tree} />}
        </Box>
      ) : (
        <Box textAlign="center" py={8}>
          <FiFolder size={32} color="#333" />
          <Text fontSize="sm" color="gray.500" mt={2}>No workspace connected</Text>
          <Text fontSize="xs" color="gray.600">Click Connect to select a folder</Text>
        </Box>
      )}
    </VStack>
  );
}

function TreeView({ node, depth = 0 }: { node: any; depth?: number }) {
  const [expanded, setExpanded] = useState(depth < 2);
  if (!node) return null;

  if (node.is_dir) {
    return (
      <Box ml={depth * 2}>
        <HStack spacing={1} cursor="pointer" onClick={() => setExpanded(!expanded)} _hover={{ bg: "whiteAlpha.50" }} borderRadius="sm" px={1}>
          <Text fontSize="xs">{expanded ? "▼" : "▶"}</Text>
          <FiFolder size={12} color="blue.400" />
          <Text fontSize="xs">{node.name}</Text>
        </HStack>
        {expanded && node.children?.map((child: any, i: number) => (
          <TreeView key={i} node={child} depth={depth + 1} />
        ))}
      </Box>
    );
  }

  return (
    <Box ml={depth * 2}>
      <HStack spacing={1} px={1} _hover={{ bg: "whiteAlpha.50" }} borderRadius="sm">
        <Text fontSize="xs" ml={4}>📄</Text>
        <Text fontSize="xs" color="gray.300">{node.name}</Text>
      </HStack>
    </Box>
  );
}

function GitPanel() {
  const [status, setStatus] = useState<any>(null);
  const [log, setLog] = useState<any[]>([]);
  const [commitMsg, setCommitMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const refresh = async () => {
    const s = await api.getGitStatus();
    setStatus(s);
    const l = await api.getGitLog(5);
    if (l.success) setLog(l.commits || []);
  };

  useEffect(() => { refresh(); }, []);

  const handleInit = async () => {
    setLoading(true);
    await api.gitInit();
    setLoading(false);
    refresh();
    toast({ title: "Git initialized", status: "success" });
  };

  const handleCommit = async () => {
    if (!commitMsg.trim()) return;
    setLoading(true);
    const result = await api.gitCommit(commitMsg.trim());
    setLoading(false);
    setCommitMsg("");
    refresh();
    toast({ title: result.success ? "Committed!" : "Commit failed", status: result.success ? "success" : "error" });
  };

  return (
    <VStack align="stretch" h="100%" p={3} spacing={3}>
      <HStack justify="space-between">
        <Text fontSize="sm" fontWeight={600}>Git</Text>
        {!status?.success || !status?.files ? (
          <Button size="xs" colorScheme="blue" variant="ghost" onClick={handleInit} isLoading={loading}>Init</Button>
        ) : null}
      </HStack>

      {status?.files && (
        <Box>
          <Text fontSize="xs" color="gray.400" mb={1}>Changes ({status.files.length})</Text>
          {status.files.slice(0, 10).map((f: any, i: number) => (
            <HStack key={i} spacing={1}>
              <Badge fontSize="xs" colorScheme={f.status === "M" ? "yellow" : f.status === "?" ? "gray" : "green"}>{f.status}</Badge>
              <Text fontSize="xs" color="gray.300" noOfLines={1}>{f.file}</Text>
            </HStack>
          ))}
          {status.files.length === 0 && <Text fontSize="xs" color="gray.600">Clean working tree</Text>}
        </Box>
      )}

      {status?.dirty && (
        <HStack>
          <Input size="xs" value={commitMsg} onChange={(e) => setCommitMsg(e.target.value)} placeholder="Commit message..." bg="#12121a" onKeyDown={(e) => e.key === "Enter" && handleCommit()} />
          <Button size="xs" colorScheme="green" onClick={handleCommit} isLoading={loading}>Commit</Button>
        </HStack>
      )}

      <Divider />
      <Text fontSize="xs" color="gray.400">Recent Commits</Text>
      {log.map((c, i) => (
        <Box key={i} p={2} bg="#0a0a0f" borderRadius="md">
          <HStack spacing={2}>
            <Badge fontSize="xs" colorScheme="purple">{c.hash}</Badge>
            <Text fontSize="xs" color="gray.300" noOfLines={1}>{c.message}</Text>
          </HStack>
          <Text fontSize="xs" color="gray.600">{c.date?.split(" ")[0]}</Text>
        </Box>
      ))}
    </VStack>
  );
}

function SessionsPanel({ onRestore }: { onRestore: (task: string, provider: string, model: string) => void }) {
  const [sessions, setSessions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const toast = useToast();

  const refresh = async () => {
    const data = await api.getSessions();
    if (data.success) setSessions(data.sessions || []);
  };

  useEffect(() => { refresh(); }, []);

  const handleDelete = async (id: string) => {
    await api.deleteSession(id);
    refresh();
    toast({ title: "Session deleted", status: "info" });
  };

  return (
    <VStack align="stretch" h="100%" p={3} spacing={3}>
      <HStack justify="space-between">
        <Text fontSize="sm" fontWeight={600}>Sessions</Text>
        <Button size="xs" variant="ghost" onClick={refresh}>Refresh</Button>
      </HStack>
      {sessions.length === 0 ? (
        <Text fontSize="xs" color="gray.600" textAlign="center" py={4}>No saved sessions yet</Text>
      ) : (
        sessions.map((s) => (
          <Box key={s.id} p={2} bg="#0a0a0f" borderRadius="md" border="1px solid #1e1e2e" _hover={{ borderColor: "blue.500" }} cursor="pointer">
            <Text fontSize="xs" color="gray.300" noOfLines={2} mb={1}>{s.task}</Text>
            <HStack spacing={2}>
              <Badge fontSize="xs" colorScheme="blue">{s.provider}</Badge>
              <Badge fontSize="xs" colorScheme="green">{s.model}</Badge>
              <Badge fontSize="xs" colorScheme="purple">{s.files_created} files</Badge>
            </HStack>
            <HStack mt={2} spacing={1}>
              <Button size="xs" colorScheme="blue" variant="ghost" onClick={() => onRestore(s.task, s.provider, s.model)}>Restore</Button>
              <Button size="xs" colorScheme="red" variant="ghost" onClick={() => handleDelete(s.id)}>Delete</Button>
            </HStack>
          </Box>
        ))
      )}
    </VStack>
  );
}

function DiffViewer({ oldContent, newContent, filePath, onClose }: { oldContent: string; newContent: string; filePath: string; onClose: () => void }) {
  const [diffData, setDiffData] = useState<any>(null);

  useEffect(() => {
    api.computeDiff(oldContent, newContent, filePath).then(setDiffData);
  }, [oldContent, newContent, filePath]);

  return (
    <Box position="fixed" inset={0} bg="blackAlpha.800" zIndex={100} display="flex" alignItems="center" justifyContent="center">
      <Box bg="#12121a" borderRadius="xl" w="900px" maxH="80vh" overflowY="auto" border="1px solid #1e1e2e">
        <HStack justify="space-between" p={4} borderBottom="1px solid #1e1e2e">
          <HStack>
            <Text fontSize="sm" fontWeight={600}>Diff: {filePath}</Text>
            {diffData && (
              <HStack spacing={2}>
                <Badge colorScheme="green">+{diffData.additions}</Badge>
                <Badge colorScheme="red">-{diffData.deletions}</Badge>
              </HStack>
            )}
          </HStack>
          <IconButton aria-label="Close" icon={<Text>×</Text>} onClick={onClose} size="sm" />
        </HStack>
        <Box p={4}>
          {diffData?.changes?.map((c: any, i: number) => (
            <HStack key={i} spacing={0}>
              <Code
                fontSize="xs" w="100%" p={1} display="block" whiteSpace="pre"
                bg={c.type === "add" ? "#0f2a0f" : c.type === "remove" ? "#2a0f0f" : "transparent"}
                color={c.type === "add" ? "green.300" : c.type === "remove" ? "red.300" : "gray.300"}
                borderRadius={0}
              >
                {c.type === "add" ? "+ " : c.type === "remove" ? "- " : "  "}{c.content}
              </Code>
            </HStack>
          ))}
          {!diffData && <Spinner size="sm" />}
        </Box>
      </Box>
    </Box>
  );
}

function DashboardPanel({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    api.getStats().then(setData);
    const interval = setInterval(() => api.getStats().then(setData), 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box position="fixed" inset={0} bg="blackAlpha.800" zIndex={100} display="flex" alignItems="center" justifyContent="center">
      <Box bg="#12121a" borderRadius="xl" w="700px" maxH="80vh" overflowY="auto" border="1px solid #1e1e2e" p={6}>
        <HStack justify="space-between" mb={6}>
          <Text fontSize="lg" fontWeight={700}>Progress Dashboard</Text>
          <IconButton aria-label="Close" icon={<Text>×</Text>} onClick={onClose} size="sm" />
        </HStack>

        {data?.current && (
          <Box bg="#0a0a0f" borderRadius="lg" p={4} mb={4} border="1px solid #1e1e2e">
            <Text fontSize="xs" color="gray.400" mb={3}>Current Task</Text>
            <Text fontSize="sm" mb={3}>{data.current.task || "No active task"}</Text>
            <SimpleGrid columns={4} spacing={3}>
              <StatCard label="Time" value={data.current.elapsed_formatted} color="blue" />
              <StatCard label="Tokens" value={String(data.current.total_tokens)} color="purple" />
              <StatCard label="Tool Calls" value={String(data.current.total_tool_calls)} color="yellow" />
              <StatCard label="Cost" value={data.current.cost_formatted} color="green" />
            </SimpleGrid>
            {data.current.phase_times?.length > 0 && (
              <Box mt={3}>
                <Text fontSize="xs" color="gray.400" mb={2}>Phase Breakdown</Text>
                {data.current.phase_times.map((p: any, i: number) => (
                  <HStack key={i} justify="space-between">
                    <Text fontSize="xs">{p.phase}</Text>
                    <Badge fontSize="xs">{p.duration?.toFixed(1)}s</Badge>
                  </HStack>
                ))}
              </Box>
            )}
          </Box>
        )}

        {data?.totals && (
          <Box bg="#0a0a0f" borderRadius="lg" p={4} mb={4} border="1px solid #1e1e2e">
            <Text fontSize="xs" color="gray.400" mb={3}>All-Time Totals</Text>
            <SimpleGrid columns={4} spacing={3}>
              <StatCard label="Tasks" value={String(data.totals.tasks_completed)} color="blue" />
              <StatCard label="Total Time" value={data.totals.total_time_formatted} color="purple" />
              <StatCard label="Total Tokens" value={String(data.totals.total_tokens)} color="yellow" />
              <StatCard label="Total Cost" value={data.totals.total_cost_formatted} color="green" />
            </SimpleGrid>
          </Box>
        )}

        {data?.history?.length > 0 && (
          <Box bg="#0a0a0f" borderRadius="lg" p={4} border="1px solid #1e1e2e">
            <Text fontSize="xs" color="gray.400" mb={3}>Task History</Text>
            {data.history.slice(-5).reverse().map((h: any, i: number) => (
              <HStack key={i} justify="space-between" py={1}>
                <Text fontSize="xs" noOfLines={1} flex={1}>{h.task}</Text>
                <Badge fontSize="xs">{h.stats?.elapsed_formatted}</Badge>
                <Badge fontSize="xs" colorScheme="green">{h.stats?.cost_formatted}</Badge>
              </HStack>
            ))}
          </Box>
        )}
      </Box>
    </Box>
  );
}

function StatCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <Box bg="#12121a" borderRadius="md" p={3} textAlign="center">
      <Text fontSize="xs" color={`${color}.400`}>{label}</Text>
      <Text fontSize="lg" fontWeight={700}>{value}</Text>
    </Box>
  );
}

function LiveDesktopPanel() {
  const [sandbox, setSandbox] = useState<any>(null);

  useEffect(() => {
    api.getSandboxStatus().then(setSandbox);
    const interval = setInterval(() => api.getSandboxStatus().then(setSandbox), 5000);
    return () => clearInterval(interval);
  }, []);

  if (!sandbox?.sandbox_running) {
    return (
      <VStack h="100%" justify="center" spacing={4}>
        <FiMonitor size={40} color="#333" />
        <Text fontSize="sm" color="gray.500">Sandbox not running</Text>
        <Button size="sm" leftIcon={<FiPlay />} onClick={async () => { await api.startSandbox(); setSandbox(await api.getSandboxStatus()); }} colorScheme="green">
          Start Sandbox
        </Button>
        {sandbox && !sandbox.docker_available && (
          <Text fontSize="xs" color="red.400">Docker is not available. Please start Docker Desktop.</Text>
        )}
      </VStack>
    );
  }

  return (
    <VStack h="100%" spacing={0}>
      <HStack w="100%" px={3} py={2} bg="#0d0d14" justify="space-between">
        <Badge colorScheme="green">Running</Badge>
        <Button size="xs" colorScheme="red" variant="ghost" onClick={async () => { await api.stopSandbox(); setSandbox(await api.getSandboxStatus()); }}>
          Stop
        </Button>
      </HStack>
      <iframe src={sandbox.novnc_url} style={{ width: "100%", flex: 1, border: "none" }} title="Sandbox Desktop" />
    </VStack>
  );
}

function TerminalView() {
  const termRef = useRef<HTMLDivElement>(null);
  const termInstance = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitAddon = useRef<any>(null);

  useEffect(() => {
    if (!termRef.current) return;

    const loadTerminal = async () => {
      const { Terminal } = await import("xterm");
      const { FitAddon } = await import("xterm-addon-fit");
      const { WebLinksAddon } = await import("xterm-addon-web-links");

      // @ts-ignore
      await import("xterm/css/xterm.css");

      const addonFit = new FitAddon();
      const addonWebLinks = new WebLinksAddon();
      fitAddon.current = addonFit;

      const term = new Terminal({
        theme: {
          background: "#0a0a0f",
          foreground: "#e0e0e0",
          cursor: "#0070e0",
          cursorAccent: "#0a0a0f",
          selectionBackground: "#0070e040",
          black: "#1e1e2e",
          red: "#f38ba8",
          green: "#a6e3a1",
          yellow: "#f9e2af",
          blue: "#89b4fa",
          magenta: "#f5c2e7",
          cyan: "#94e2d5",
          white: "#cdd6f4",
        },
        fontSize: 13,
        fontFamily: "Cascadia Code, Fira Code, Consolas, monospace",
        cursorBlink: true,
        cursorStyle: "bar",
        scrollback: 5000,
      });

      term.loadAddon(addonFit);
      term.loadAddon(addonWebLinks);
      if (termRef.current) {
        term.open(termRef.current);
      }
      termInstance.current = term;

      term.writeln("\x1b[1;34m╔══════════════════════════════════════╗\x1b[0m");
      term.writeln("\x1b[1;34m║       Devin Clone Terminal           ║\x1b[0m");
      term.writeln("\x1b[1;34m╚══════════════════════════════════════╝\x1b[0m");
      term.writeln("\r\nConnecting...\r\n");

      const socket = api.createTerminalWs();
      wsRef.current = socket;

      socket.onopen = () => {
        term.clear();
        term.writeln("\x1b[1;32mConnected to terminal.\x1b[0m\r\n");
        addonFit.fit();
      };

      socket.onmessage = (event) => {
        term.write(event.data);
      };

      socket.onclose = () => {
        term.writeln("\r\n\x1b[1;31m[Disconnected from terminal]\x1b[0m");
      };

      socket.onerror = () => {
        term.writeln("\r\n\x1b[1;31m[Connection error]\x1b[0m");
      };

      term.onData((data: string) => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(data);
        }
      });

      const observer = new ResizeObserver(() => {
        addonFit.fit();
      });
      if (termRef.current) {
        observer.observe(termRef.current);
      }
    };

    loadTerminal();

    return () => {
      wsRef.current?.close();
      termInstance.current?.dispose();
    };
  }, []);

  return (
    <Box h="100%" w="100%" bg="#0a0a0f" p={2}>
      <div ref={termRef} style={{ width: "100%", height: "100%" }} />
    </Box>
  );
}

function ProviderCard({ provider, onSave, onTest, onSaveModel }: { provider: Provider; onSave: (id: string, key: string) => Promise<void>; onTest: (id: string, model: string) => Promise<void>; onSaveModel: (id: string, model: string) => Promise<void> }) {
  const [key, setKey] = useState("");
  const [model, setModel] = useState(provider.selected_model || "");
  const [models, setModels] = useState<any[]>([]);
  const [freeOnly, setFreeOnly] = useState(false);
  const [loading, setLoading] = useState(false);
  const [testing, setTesting] = useState(false);
  const [showBrowserLogin, setShowBrowserLogin] = useState(false);
  const toast = useColorModeValue("gray", "gray");
  const bg = useColorModeValue("white", "#0a0a0f");
  const borderColor = provider.has_key ? "green.500" : "#1e1e2e";

  useEffect(() => {
    api.getModels(provider.id, freeOnly).then((data) => {
      setModels(data.models || []);
      if (data.selected) setModel(data.selected);
    }).catch(() => {});
  }, [provider.id, freeOnly]);

  const handleSaveKey = async () => {
    if (!key.trim()) return;
    setLoading(true);
    await onSave(provider.id, key.trim());
    setLoading(false);
  };

  const handleTest = async () => {
    if (!model) return;
    setTesting(true);
    await onTest(provider.id, model);
    setTesting(false);
  };

  const handleSaveModel = async () => {
    if (!model) return;
    await onSaveModel(provider.id, model);
  };

  return (
    <Box bg={bg} borderRadius="lg" p={4} border={`1px solid ${borderColor}`} _hover={{ borderColor: provider.has_key ? "green.300" : "blue.500" }} transition="all 0.2s">
      <HStack justify="space-between" mb={3}>
        <HStack spacing={2}>
          <Text fontSize="sm" fontWeight={600}>{provider.name}</Text>
          {provider.has_key && <FiCheckCircle size={14} color="green" />}
        </HStack>
        {provider.supports_browser_login && (
          <Button size="xs" variant="ghost" colorScheme="purple" onClick={() => setShowBrowserLogin(!showBrowserLogin)}>
            <FiGlobe size={12} /> <Text ml={1} fontSize="xs">Browser</Text>
          </Button>
        )}
      </HStack>

      <Text fontSize="xs" color="gray.400" mb={1}>API Key</Text>
      <HStack mb={3}>
        <Input
          size="sm" type="password"
          placeholder={provider.has_key ? "•••••••• (saved)" : "Enter API key..."}
          value={key} onChange={(e) => setKey(e.target.value)}
          bg="#12121a" flex={1}
        />
        <Button size="sm" colorScheme="blue" onClick={handleSaveKey} isLoading={loading} isDisabled={!key.trim()}>Save</Button>
        <Button size="sm" colorScheme="green" variant="outline" onClick={handleTest} isLoading={testing} isDisabled={!model}>Test</Button>
      </HStack>

      {showBrowserLogin && provider.supports_browser_login && (
        <Box mb={3} p={2} bg="#1a1520" borderRadius="md" border="1px solid #2d2540">
          <Text fontSize="xs" color="gray.500" mb={2}>Browser login — no API key needed</Text>
          <Button size="xs" colorScheme="purple" onClick={async () => {
            const result = await api.startBrowserLogin(provider.id);
            alert(result.message || result.error);
          }}>Open Browser Login</Button>
        </Box>
      )}

      <HStack justify="space-between" mb={1}>
        <Text fontSize="xs" color="gray.400">Model</Text>
        <HStack spacing={2}>
          <Switch size="sm" isChecked={freeOnly} onChange={(e) => setFreeOnly(e.target.checked)} />
          <Text fontSize="2xs" color="gray.500">Free only</Text>
        </HStack>
      </HStack>
      <HStack>
        <Select size="sm" value={model} onChange={(e) => setModel(e.target.value)} bg="#12121a" flex={1} placeholder="Select model">
          {models.map((m: any) => (
            <option key={m.id} value={m.id}>
              {m.name} {m.is_free ? "🆓" : ""} {m.tool_calling_supported ? "🔧" : ""}
            </option>
          ))}
        </Select>
        <Button size="sm" colorScheme="blue" variant="ghost" onClick={handleSaveModel} isDisabled={!model}>Set</Button>
      </HStack>
    </Box>
  );
}

function SettingsPage({ onClose }: { onClose: () => void }) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [searchKeys, setSearchKeys] = useState<any>({});
  const [tavilyKey, setTavilyKey] = useState("");
  const [braveKey, setBraveKey] = useState("");
  const [activeBackend, setActiveBackend] = useState("tavily");
  const [searchQuery, setSearchQuery] = useState("");
  const toast = useToast();

  useEffect(() => {
    api.getProviders().then((data) => setProviders(data.providers));
    api.getSearchKeys().then((data) => setSearchKeys(data.search_keys));
  }, []);

  const handleSaveKey = async (providerId: string, key: string) => {
    const result = await api.saveKey(providerId, key);
    toast({ title: result.success ? "Key saved" : "Error", status: result.success ? "success" : "error" });
    const data = await api.getProviders();
    setProviders(data.providers);
  };

  const handleTestKey = async (providerId: string, model: string) => {
    const result = await api.testProvider(providerId, model);
    toast({
      title: result.success ? "Connection OK" : "Failed",
      description: result.error || result.response,
      status: result.success ? "success" : "error",
    });
  };

  const handleSaveModel = async (providerId: string, model: string) => {
    await api.post("/model-selection", { provider_id: providerId, model });
    toast({ title: "Model selected", status: "success" });
  };

  const handleSaveSearchKey = async (backend: string, key: string) => {
    await api.saveSearchKey(backend, key);
    toast({ title: `${backend} key saved`, status: "success" });
    api.getSearchKeys().then((data) => setSearchKeys(data.search_keys));
  };

  const handleTestSearch = async (backend: string) => {
    const result = backend === "tavily" ? await api.testTavily() : await api.testBrave();
    toast({ title: result.success ? "Key valid" : "Invalid", description: result.error || result.response, status: result.success ? "success" : "error" });
  };

  const filtered = providers.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) || p.id.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <Box position="fixed" inset={0} bg="blackAlpha.800" zIndex={100} display="flex" alignItems="center" justifyContent="center">
      <Box bg="#12121a" borderRadius="xl" w="900px" maxH="85vh" overflowY="auto" border="1px solid #1e1e2e" p={6}>
        <HStack justify="space-between" mb={4}>
          <Text fontSize="lg" fontWeight={700}>Settings & Providers</Text>
          <HStack spacing={3}>
            <Input size="sm" placeholder="Search providers..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} bg="#0a0a0f" w="200px" />
            <IconButton aria-label="Close" icon={<Text>×</Text>} onClick={onClose} size="sm" />
          </HStack>
        </HStack>

        <HStack mb={2} spacing={4}>
          <Badge colorScheme="green">{providers.filter(p => p.has_key).length} configured</Badge>
          <Badge colorScheme="gray">{providers.filter(p => !p.has_key).length} unconfigured</Badge>
          <Badge colorScheme="blue">{providers.length} total</Badge>
        </HStack>

        <SimpleGrid columns={2} spacing={3} mb={6}>
          {filtered.map((p) => (
            <ProviderCard
              key={p.id}
              provider={p}
              onSave={handleSaveKey}
              onTest={handleTestKey}
              onSaveModel={handleSaveModel}
            />
          ))}
        </SimpleGrid>

        <Divider my={4} />
        <Text fontSize="sm" fontWeight={600} mb={3}>Web Search</Text>
        <Box bg="#0a0a0f" borderRadius="lg" p={4} border="1px solid #1e1e2e">
          {["tavily", "brave"].map((b) => (
            <HStack key={b} mb={2}>
              <Text fontSize="xs" w="80" textTransform="capitalize">{b}:</Text>
              <Input
                size="sm" type="password" placeholder={`${b} key...`}
                onChange={(e) => b === "tavily" ? setTavilyKey(e.target.value) : setBraveKey(e.target.value)}
                bg="#12121a" flex={1}
              />
              <Button size="xs" onClick={() => handleSaveSearchKey(b, b === "tavily" ? tavilyKey : braveKey)} colorScheme="blue" variant="ghost">Save</Button>
              <Button size="xs" onClick={() => handleTestSearch(b)} colorScheme="green" variant="ghost">Test</Button>
              {searchKeys[b]?.configured && <FiCheckCircle size={12} color="green" />}
            </HStack>
          ))}
          <Divider my={3} />
          <HStack>
            <Text fontSize="xs">Active backend:</Text>
            <Select size="xs" value={activeBackend} onChange={(e) => { setActiveBackend(e.target.value); api.post("/search-backend", { backend: e.target.value }); }} w="120px">
              <option value="tavily">Tavily</option>
              <option value="brave">Brave</option>
            </Select>
          </HStack>
        </Box>
      </Box>
    </Box>
  );
}

export default function App() {
  const [messages, setMessages] = useState<AgentEvent[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [currentAgent, setCurrentAgent] = useState("");
  const [completedAgents, setCompletedAgents] = useState<string[]>([]);
  const [showSettings, setShowSettings] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [showDiff, setShowDiff] = useState(false);
  const [diffData, setDiffData] = useState({ old: "", new: "", file: "" });
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("openai");
  const [selectedModel, setSelectedModel] = useState("gpt-4o");
  const [sidebarModels, setSidebarModels] = useState<any[]>([]);
  const [sidebarFreeOnly, setSidebarFreeOnly] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [rightTab, setRightTab] = useState(0);
  const toast = useToast();

  useEffect(() => {
    api.getProviders().then((data) => {
      setProviders(data.providers);
      const configured = data.providers.find((p: Provider) => p.has_key);
      if (configured) {
        setSelectedProvider(configured.id);
        if (configured.selected_model) setSelectedModel(configured.selected_model);
      }
    });
  }, [showSettings]);

  useEffect(() => {
    if (selectedProvider) {
      api.getModels(selectedProvider, sidebarFreeOnly).then((data) => {
        setSidebarModels(data.models || []);
        if (data.selected) setSelectedModel(data.selected);
      }).catch(() => {});
    }
  }, [selectedProvider, sidebarFreeOnly]);

  const connectWs = useCallback(() => {
    const socket = api.createWebSocket();
    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.event === "content" || data.event === "tool_call" || data.event === "tool_result" || data.event === "error" || data.event === "agent_start" || data.event === "monologue" || data.event === "context_compressed") {
        setMessages((prev) => [...prev, data]);
      }

      if (data.event === "agent_start") {
        const agentName = data.agent || "";
        setCurrentAgent(agentName);
        const completed = agentName.toLowerCase();
        if (completed.includes("architect")) setCompletedAgents((prev) => [...prev, "plan"]);
        if (completed.includes("coder")) setCompletedAgents((prev) => [...prev, "architect"]);
        if (completed.includes("reviewer")) setCompletedAgents((prev) => [...prev, "code"]);
        if (completed.includes("tester")) setCompletedAgents((prev) => [...prev, "reviewer"]);
      }
      if (data.event === "agent_done") {
        if (data.agent) setCompletedAgents((prev) => [...prev, data.agent.toLowerCase()]);
      }
      if (data.event === "workflow_done" || data.event === "done" || data.event === "stopped") {
        setIsRunning(false);
        if (data.event === "workflow_done") setCompletedAgents(["plan", "architect", "code", "reviewer", "tester"]);
      }
      if (data.event === "paused") toast({ title: "Paused", status: "warning", duration: 2000 });
      if (data.event === "resumed") toast({ title: "Resumed", status: "info", duration: 2000 });
    };
    socket.onclose = () => setTimeout(connectWs, 3000);
    socket.onerror = () => {};
    setWs(socket);
    return socket;
  }, []);

  useEffect(() => {
    const socket = connectWs();
    return () => socket.close();
  }, [connectWs]);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "Enter") { e.preventDefault(); const el = document.querySelector("input[placeholder='Describe your task...']") as HTMLInputElement; if (el?.value?.trim()) { handleSend(el.value.trim()); el.value = ""; } }
      if (e.ctrlKey && e.key === "p") { e.preventDefault(); handlePause(); }
      if (e.ctrlKey && e.key === ".") { e.preventDefault(); handleStop(); }
      if (e.ctrlKey && e.key === "e") { e.preventDefault(); api.downloadExport(); }
      if (e.ctrlKey && e.key === ",") { e.preventDefault(); setShowSettings(true); }
      if (e.ctrlKey && e.key === "d") { e.preventDefault(); setShowDashboard(true); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [ws]);

  const handleSend = (task: string) => {
    setMessages([{ event: "user_message", content: task }]);
    setCompletedAgents([]);
    setCurrentAgent("");
    setIsRunning(true);
    ws?.send(JSON.stringify({ type: "run", task, provider: selectedProvider, model: selectedModel }));
  };

  const handlePause = () => ws?.send(JSON.stringify({ type: "control", action: "pause" }));
  const handleResume = () => ws?.send(JSON.stringify({ type: "control", action: "resume" }));
  const handleStop = () => { ws?.send(JSON.stringify({ type: "control", action: "stop" })); setIsRunning(false); };

  const startVoice = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      const chunks: BlobPart[] = [];
      mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
      mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        stream.getTracks().forEach(t => t.stop());
        toast({ title: "Processing voice...", status: "info", duration: 3000 });
      };
      mediaRecorder.start();
      setIsRecording(true);
      setTimeout(() => { mediaRecorder.stop(); setIsRecording(false); }, 15000);
      toast({ title: "Recording... (max 15s)", status: "info", duration: 2000 });
    } catch {
      toast({ title: "Microphone access denied", status: "error" });
    }
  };

  return (
    <Flex h="100vh" direction="column">
      <TitleBar />
      <Flex flex={1} overflow="hidden">
        <Box w="280px" bg="#0d0d14" borderRight="1px solid #1e1e2e" overflowY="auto">
          <VStack align="stretch" p={3} spacing={3}>
            <Text fontSize="xs" fontWeight={600} color="gray.500" px={2}>PROVIDER</Text>
            <Select size="sm" value={selectedProvider} onChange={(e) => setSelectedProvider(e.target.value)} bg="#12121a">
              {providers.map((p) => (
                <option key={p.id} value={p.id}>{p.name} {p.has_key ? "✓" : ""}</option>
              ))}
            </Select>
            <Text fontSize="xs" fontWeight={600} color="gray.500" px={2}>MODEL</Text>
            <HStack px={2} mb={1}>
              <Switch size="sm" isChecked={sidebarFreeOnly} onChange={(e) => setSidebarFreeOnly(e.target.checked)} />
              <Text fontSize="2xs" color="gray.500">Free models only</Text>
            </HStack>
            <Select size="sm" value={selectedModel} onChange={(e) => setSelectedModel(e.target.value)} bg="#12121a" placeholder="Select model">
              {sidebarModels.map((m: any) => (
                <option key={m.id} value={m.id}>
                  {m.name} {m.is_free ? "🆓 FREE" : ""} {m.tool_calling_supported ? "🔧" : ""}
                </option>
              ))}
            </Select>
            <Divider />
            <Button size="sm" leftIcon={<FiSettings />} onClick={() => setShowSettings(true)} variant="ghost" justifyContent="flex-start">Settings</Button>
            <Button size="sm" leftIcon={<FiFolder />} onClick={() => setRightTab(0)} variant="ghost" justifyContent="flex-start">Workspace</Button>
            <Button size="sm" leftIcon={<FiTerminal />} onClick={() => setRightTab(2)} variant="ghost" justifyContent="flex-start">Terminal</Button>
            <Button size="sm" leftIcon={<FiMonitor />} onClick={() => setRightTab(1)} variant="ghost" justifyContent="flex-start">Live Desktop</Button>
            <Button size="sm" leftIcon={<FiDownload />} onClick={() => api.downloadExport()} variant="ghost" justifyContent="flex-start">Export</Button>
            <Button size="sm" leftIcon={<FiZap />} onClick={() => setShowDashboard(true)} variant="ghost" justifyContent="flex-start">Dashboard</Button>
            <Divider />
            <Text fontSize="2xs" color="gray.600" px={2}>Ctrl+Enter Send · Ctrl+P Pause · Ctrl+. Stop · Ctrl+E Export · Ctrl+, Settings · Ctrl+D Dashboard</Text>
          </VStack>
        </Box>

        <Box flex={1} position="relative">
          <ChatPanel
            messages={messages} onSend={handleSend} isRunning={isRunning}
            onPause={handlePause} onResume={handleResume} onStop={handleStop}
            currentAgent={currentAgent} completedAgents={completedAgents}
          />
          {isRecording && (
            <Box position="absolute" bottom="80px" left="50%" transform="translateX(-50%)" bg="red.600" borderRadius="full" px={4} py={2}>
              <HStack><Box w={2} h={2} borderRadius="full" bg="white" animation="pulse 1s infinite" /><Text fontSize="xs" fontWeight={600}>Recording...</Text></HStack>
            </Box>
          )}
        </Box>

        <Box w="300px" bg="#0d0d14" borderLeft="1px solid #1e1e2e" overflowY="auto">
          <Tabs variant="enclosed" size="sm" index={rightTab} onChange={setRightTab}>
            <TabList bg="#08080d">
              <Tab>Workspace</Tab>
              <Tab>Desktop</Tab>
              <Tab>Terminal</Tab>
              <Tab>Git</Tab>
              <Tab>Sessions</Tab>
            </TabList>
            <TabPanels>
              <TabPanel p={0}><WorkspacePanel /></TabPanel>
              <TabPanel p={0} h="calc(100vh - 120px)"><LiveDesktopPanel /></TabPanel>
              <TabPanel p={0} h="calc(100vh - 120px)"><TerminalView /></TabPanel>
              <TabPanel p={0}><GitPanel /></TabPanel>
              <TabPanel p={0}><SessionsPanel onRestore={(task, prov, mod) => { setSelectedProvider(prov); setSelectedModel(mod); handleSend(task); }} /></TabPanel>
            </TabPanels>
          </Tabs>
        </Box>
      </Flex>

      {showSettings && <SettingsPage onClose={() => setShowSettings(false)} />}
      {showDashboard && <DashboardPanel onClose={() => setShowDashboard(false)} />}
      {showDiff && <DiffViewer oldContent={diffData.old} newContent={diffData.new} filePath={diffData.file} onClose={() => setShowDiff(false)} />}
    </Flex>
  );
}
