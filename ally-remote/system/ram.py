"""
ram.py — Liberação de RAM sob demanda (Windows).

Duas ações, na mesma linha do que ferramentas como RAMMap/ISLC fazem:

1. EmptyWorkingSet em todos os processos acessíveis (psapi) — pede ao
   Windows para aparar o working set de cada processo. Páginas não usadas
   vão para a standby list / pagefile.

2. Purge da Standby List via NtSetSystemInformation(SystemMemoryListInformation,
   MemoryPurgeStandbyList). Isso converte cache "em espera" em memória
   realmente livre. Requer privilégio SeProfileSingleProcessPrivilege
   (ou seja: rodar como Administrador).

Observação honesta: o Windows gerencia memória bem sozinho; isso é útil
principalmente quando um jogo reclama de RAM e há muita standby list
acumulada. O efeito é imediato mas o sistema volta a preencher o cache
com o tempo — é esperado.
"""

import ctypes
from ctypes import wintypes

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SET_QUOTA = 0x0100

SE_PRIVILEGE_ENABLED = 0x2
TOKEN_ADJUST_PRIVILEGES = 0x20
TOKEN_QUERY = 0x8

SystemMemoryListInformation = 80
MemoryPurgeStandbyList = 4


class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength", wintypes.DWORD),
        ("dwMemoryLoad", wintypes.DWORD),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


class LUID(ctypes.Structure):
    _fields_ = [("LowPart", wintypes.DWORD), ("HighPart", wintypes.LONG)]


class LUID_AND_ATTRIBUTES(ctypes.Structure):
    _fields_ = [("Luid", LUID), ("Attributes", wintypes.DWORD)]


class TOKEN_PRIVILEGES(ctypes.Structure):
    _fields_ = [("PrivilegeCount", wintypes.DWORD), ("Privileges", LUID_AND_ATTRIBUTES * 1)]


def memory_status() -> dict:
    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    return {
        "total_mb": st.ullTotalPhys // (1024 * 1024),
        "avail_mb": st.ullAvailPhys // (1024 * 1024),
        "load_pct": st.dwMemoryLoad,
    }


def _enable_privilege(name: str) -> bool:
    adv = ctypes.windll.advapi32
    k32 = ctypes.windll.kernel32
    token = wintypes.HANDLE()
    if not adv.OpenProcessToken(
        k32.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(token)
    ):
        return False
    luid = LUID()
    if not adv.LookupPrivilegeValueW(None, name, ctypes.byref(luid)):
        k32.CloseHandle(token)
        return False
    tp = TOKEN_PRIVILEGES()
    tp.PrivilegeCount = 1
    tp.Privileges[0].Luid = luid
    tp.Privileges[0].Attributes = SE_PRIVILEGE_ENABLED
    ok = adv.AdjustTokenPrivileges(token, False, ctypes.byref(tp), 0, None, None)
    err = k32.GetLastError()
    k32.CloseHandle(token)
    return bool(ok) and err == 0


def _empty_working_sets() -> int:
    """Retorna quantos processos foram aparados."""
    psapi = ctypes.windll.psapi
    k32 = ctypes.windll.kernel32
    arr = (wintypes.DWORD * 4096)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(needed)):
        return 0
    count = needed.value // ctypes.sizeof(wintypes.DWORD)
    trimmed = 0
    for pid in arr[:count]:
        if pid == 0:
            continue
        h = k32.OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_SET_QUOTA, False, pid)
        if not h:
            continue
        if psapi.EmptyWorkingSet(h):
            trimmed += 1
        k32.CloseHandle(h)
    return trimmed


def _purge_standby_list() -> bool:
    if not _enable_privilege("SeProfileSingleProcessPrivilege"):
        return False
    ntdll = ctypes.windll.ntdll
    cmd = ctypes.c_int(MemoryPurgeStandbyList)
    status = ntdll.NtSetSystemInformation(
        SystemMemoryListInformation, ctypes.byref(cmd), ctypes.sizeof(cmd)
    )
    return status == 0


def free_ram() -> dict:
    before = memory_status()
    trimmed = _empty_working_sets()
    standby_ok = _purge_standby_list()
    after = memory_status()
    return {
        "before_avail_mb": before["avail_mb"],
        "after_avail_mb": after["avail_mb"],
        "freed_mb": after["avail_mb"] - before["avail_mb"],
        "processes_trimmed": trimmed,
        "standby_purged": standby_ok,
        "total_mb": after["total_mb"],
        "load_pct": after["load_pct"],
    }
