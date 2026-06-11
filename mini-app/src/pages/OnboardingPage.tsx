import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppStore } from "@/stores/appStore";
import { authApi } from "@/api/auth";
import { teamsApi } from "@/api/teams";
import { getTgUser, tg } from "@/lib/tg";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import logoUrl from "../../assets/logo.png";

export function OnboardingPage() {
  const navigate = useNavigate();
  const { setJwt, setTgUser, setActiveTeam, isAuthenticated } = useAppStore();
  const [step, setStep] = useState<"loading" | "welcome" | "join">("loading");
  const [inviteInput, setInviteInput] = useState("");
  const [joining, setJoining] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate("/", { replace: true });
      return;
    }
    autoLogin();
  }, []);

  const autoLogin = async () => {
    const tgUser = getTgUser();
    if (tgUser) {
      setTgUser(tgUser);
    }

    const initData = tg?.initData;
    if (!initData) {
      setStep("welcome");
      return;
    }

    try {
      const res = await authApi.loginWithInitData();
      setJwt(res.token);
      try {
        const teams = await teamsApi.listMemberOf();
        if (teams.length > 0) setActiveTeam(teams[0]);
      } catch {
        // non-critical
      }
      navigate("/", { replace: true });
    } catch {
      setStep("welcome");
    }
  };

  const handleJoinTeam = async () => {
    const raw = inviteInput.trim();
    const teamId = raw.includes("/") ? (raw.split("/").pop() ?? raw) : raw;
    if (!teamId) return;

    const tgUser = getTgUser();
    if (!tgUser) {
      toast.error("Не удалось получить данные Telegram");
      return;
    }

    setJoining(true);
    try {
      const res = await authApi.joinTeam(teamId, tgUser.id);
      setJwt(res.token);
      navigate("/onboarding/yougile", { replace: true });
    } catch (e: any) {
      toast.error(
        e?.response?.data?.detail ?? "Неверная ссылка или команда не найдена",
      );
    } finally {
      setJoining(false);
    }
  };

  if (step === "loading") {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }

  if (step === "join") {
    return (
      <div className="flex flex-col min-h-screen px-6 pt-12 pb-8">
        <button
          onClick={() => setStep("welcome")}
          className="text-primary text-sm mb-8"
        >
          ← Назад
        </button>
        <h1 className="text-2xl font-bold mb-2">Войти в команду</h1>
        <p className="text-muted-foreground text-sm mb-8">
          Вставьте инвайт-ссылку или ID команды
        </p>

        <Input
          placeholder="https://t.me/bot?start=... или UUID"
          value={inviteInput}
          onChange={(e) => setInviteInput(e.target.value)}
          className="mb-4"
        />

        <Button
          onClick={handleJoinTeam}
          disabled={!inviteInput.trim() || joining}
          className="w-full"
        >
          {joining ? "Вход..." : "Войти"}
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen px-6 pb-8">
      <div className="flex-1 flex flex-col items-center justify-center text-center">
        <div className="mb-6 h-28 w-28">
          <img src={logoUrl} alt="TeamPilot" className="h-full w-full object-contain" />
        </div>
        <h1 className="text-2xl font-bold mb-3">TeamPilot</h1>
        <p className="text-muted-foreground text-sm leading-relaxed">
          Бот-ассистент для вашей команды. Управляйте задачами, стендапами и
          дедлайнами прямо в Telegram.
        </p>
      </div>

      <div className="space-y-3">
        <Button
          variant="outline"
          className="w-full"
          onClick={() => {
            window.open("https://t.me/prorab_bot?start=pay", "_blank");
          }}
        >
          💳 Создать команду
        </Button>
        <Button
          variant="secondary"
          className="w-full"
          onClick={() => setStep("join")}
        >
          🔗 Войти по инвайт-ссылке
        </Button>
      </div>
    </div>
  );
}
