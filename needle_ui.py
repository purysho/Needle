from __future__ import annotations
import os, re, subprocess, sys, threading, time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from needle.indexer import SearchIndex, runtime_path

BG='#0f1318'; PANEL='#171d24'; PANEL2='#1d252e'; FG='#edf2f7'; MUTED='#98a2ad'; ACCENT='#c9f45b'; BORDER='#2b3541'

def style_app(root):
    root.configure(bg=BG); s=ttk.Style(root)
    try:s.theme_use('clam')
    except tk.TclError:pass
    s.configure('.',background=BG,foreground=FG,fieldbackground=PANEL,font=('Segoe UI',10))
    s.configure('TFrame',background=BG);s.configure('Panel.TFrame',background=PANEL)
    s.configure('TLabel',background=BG,foreground=FG);s.configure('Muted.TLabel',background=BG,foreground=MUTED)
    s.configure('Title.TLabel',background=BG,foreground=FG,font=('Segoe UI Semibold',20))
    s.configure('CardLabel.TLabel',background=PANEL,foreground=MUTED,font=('Segoe UI',9))
    s.configure('TButton',background=PANEL2,foreground=FG,padding=(10,7),bordercolor=BORDER);s.map('TButton',background=[('active','#26313c')])
    s.configure('Accent.TButton',background=ACCENT,foreground='#111417',padding=(11,7),font=('Segoe UI Semibold',10));s.map('Accent.TButton',background=[('active','#d8ff78')])
    s.configure('TEntry',fieldbackground=PANEL,foreground=FG,insertcolor=FG,bordercolor=BORDER,padding=7)
    s.configure('TCombobox',fieldbackground=PANEL,background=PANEL,foreground=FG,arrowcolor=FG,padding=5)
    s.configure('Treeview',background=PANEL,fieldbackground=PANEL,foreground=FG,bordercolor=BORDER,rowheight=28)
    s.configure('Treeview.Heading',background=PANEL2,foreground=FG,font=('Segoe UI Semibold',9),relief='flat');s.map('Treeview',background=[('selected','#2b3b48')])
    s.configure('Horizontal.TProgressbar',troughcolor=PANEL,background=ACCENT,bordercolor=PANEL)

def human_bytes(n):
    n=float(n or 0)
    for u in ('B','KB','MB','GB','TB'):
        if n<1024 or u=='TB':return f'{n:.0f} {u}' if u=='B' else f'{n:.1f} {u}'
        n/=1024

def native_path(p):return runtime_path(p)

def open_file(p):
    p=native_path(p)
    if sys.platform.startswith('win'):os.startfile(str(p))
    elif sys.platform=='darwin':subprocess.Popen(['open',str(p)])
    else:subprocess.Popen(['xdg-open',str(p)])

def reveal_file(p):
    p=native_path(p)
    if sys.platform.startswith('win'):subprocess.Popen(['explorer','/select,',os.path.normpath(str(p))])
    elif sys.platform=='darwin':subprocess.Popen(['open','-R',str(p)])
    else:subprocess.Popen(['xdg-open',str(p.parent)])

class App:
    PAGE_SIZE=200
    def __init__(self,root):
        self.root=root;style_app(root);root.title('Needle — Local Search');root.geometry('1220x800');root.minsize(920,620)
        self.index=None;self.index_path=None;self.all_results=[];self.page=0;self.generation=0;self.auto_job=None;self.busy=False
        self.query=tk.StringVar();self.ext=tk.StringVar(value='All types');self.status=tk.StringVar(value='Open an index or build one from a folder.');self.auto=tk.BooleanVar(value=False)
        self.build_ui()

    def build_ui(self):
        top=ttk.Frame(self.root,padding=(22,18,22,8));top.pack(fill='x')
        ttk.Label(top,text='Needle',style='Title.TLabel').pack(side='left');ttk.Label(top,text='Local full-text search',style='Muted.TLabel').pack(side='left',padx=(14,0),pady=(6,0))
        ttk.Button(top,text='Build New Index',command=self.build_new).pack(side='right');ttk.Button(top,text='Open Index',command=self.open_index).pack(side='right',padx=(0,8));ttk.Button(top,text='Update Index',command=self.update_index).pack(side='right',padx=(0,8))
        info=ttk.Frame(self.root,padding=(22,2,22,10));info.pack(fill='x');self.index_label=ttk.Label(info,text='No index loaded',style='Muted.TLabel');self.index_label.pack(side='left',fill='x',expand=True)
        ttk.Checkbutton(info,text='Auto-update every 60s',variable=self.auto,command=self.toggle_auto).pack(side='right')
        search=ttk.Frame(self.root,padding=(22,4,22,8));search.pack(fill='x')
        self.entry=ttk.Entry(search,textvariable=self.query,font=('Segoe UI',13));self.entry.pack(side='left',fill='x',expand=True);self.entry.bind('<Return>',lambda e:self.search())
        self.combo=ttk.Combobox(search,textvariable=self.ext,values=['All types'],state='readonly',width=18);self.combo.pack(side='left',padx=(8,0));ttk.Button(search,text='Search',style='Accent.TButton',command=self.search).pack(side='left',padx=(8,0))
        hint=ttk.Frame(self.root,padding=(22,0,22,6));hint.pack(fill='x');ttk.Label(hint,text='Blank query = browse the selected file type. Quotes = exact phrase. Typo tolerance is automatic.',style='Muted.TLabel').pack(side='left')
        self.progress=ttk.Progressbar(self.root,mode='indeterminate');self.progress.pack(fill='x',padx=22)
        paned=ttk.Panedwindow(self.root,orient='vertical');paned.pack(fill='both',expand=True,padx=22,pady=(10,8))
        rf=ttk.Frame(paned);paned.add(rf,weight=4)
        cols=('name','ext','score','size','modified','path');self.results=ttk.Treeview(rf,columns=cols,show='headings')
        for c,h,w in [('name','Name',250),('ext','Type',70),('score','Score',80),('size','Size',90),('modified','Modified',150),('path','Path',520)]:self.results.heading(c,text=h);self.results.column(c,width=w,anchor='w' if c in ('name','path') else 'center')
        sy=ttk.Scrollbar(rf,orient='vertical',command=self.results.yview);self.results.configure(yscrollcommand=sy.set);self.results.pack(side='left',fill='both',expand=True);sy.pack(side='right',fill='y')
        self.results.bind('<<TreeviewSelect>>',self.select_result);self.results.bind('<Double-1>',lambda e:self.open_selected())
        detail=ttk.Frame(paned,style='Panel.TFrame',padding=10);paned.add(detail,weight=1);bar=ttk.Frame(detail,style='Panel.TFrame');bar.pack(fill='x')
        self.detail=ttk.Label(bar,text='No result selected',style='CardLabel.TLabel');self.detail.pack(side='left',fill='x',expand=True)
        ttk.Button(bar,text='Copy Path',command=self.copy_path).pack(side='right');ttk.Button(bar,text='Reveal',command=self.reveal_selected).pack(side='right',padx=(0,7));ttk.Button(bar,text='Open',command=self.open_selected).pack(side='right',padx=(0,7))
        self.snippet=tk.Text(detail,height=5,wrap='word',bg=PANEL,fg=FG,relief='flat',font=('Segoe UI',10),padx=4,pady=7);self.snippet.pack(fill='both',expand=True);self.snippet.configure(state='disabled')
        foot=ttk.Frame(self.root,padding=(22,5,22,14));foot.pack(fill='x');ttk.Label(foot,textvariable=self.status,style='Muted.TLabel').pack(side='left',fill='x',expand=True)
        ttk.Button(foot,text='Previous',command=self.prev_page).pack(side='right');ttk.Button(foot,text='Next',command=self.next_page).pack(side='right',padx=(0,7))

    def begin_busy(self,msg):self.busy=True;self.status.set(msg);self.progress.start(12)
    def end_busy(self):self.busy=False;self.progress.stop()

    def open_index(self):
        p=filedialog.askopenfilename(title='Open Needle index',filetypes=[('Needle index','*.json'),('JSON','*.json'),('All files','*.*')])
        if p:self.load_index(Path(p))

    def load_index(self,p):
        self.begin_busy('Loading index…')
        def work():
            try:i=SearchIndex.load(p);e=None
            except Exception as x:i=None;e=x
            self.root.after(0,lambda:self.loaded(Path(p),i,e))
        threading.Thread(target=work,daemon=True).start()

    def loaded(self,p,i,e):
        self.end_busy()
        if e:messagebox.showerror('Needle',str(e));return
        self.index=i;self.index_path=p;self.refresh_index_info();self.all_results=[];self.render_page();self.status.set('Index ready.')

    def refresh_index_info(self):
        st=self.index.stats();self.index_label.configure(text=f"{self.index_path}   •   {st['documents']:,} files   •   {st['terms']:,} terms   •   {human_bytes(st['total_size'])}")
        self.combo['values']=['All types']+list(st['by_extension'].keys())
        if self.ext.get() not in self.combo['values']:self.ext.set('All types')

    def build_new(self):
        folder=filedialog.askdirectory(title='Choose folder to index')
        if not folder:return
        out=filedialog.asksaveasfilename(title='Save Needle index',defaultextension='.json',initialfile='needle-index.json',filetypes=[('Needle index','*.json')])
        if out:self.build_index([folder],Path(out),True,False)

    def update_index(self,automatic=False):
        if not self.index or not self.index_path:
            if not automatic:messagebox.showinfo('Needle','Open an index first.')
            return
        roots=self.index.data.get('roots',[])
        if not roots:
            if not automatic:messagebox.showinfo('Needle','This index has no recorded roots.')
            return
        self.build_index(roots,self.index_path,False,automatic)

    def build_index(self,roots,out,new,automatic):
        if self.busy:return
        self.begin_busy('Updating index…' if not new else 'Building index…')
        def work():
            try:
                idx=SearchIndex() if new else SearchIndex.load(out);stats=idx.build(roots);idx.save(out);err=None
            except Exception as x:idx=None;stats=None;err=x
            self.root.after(0,lambda:self.built(out,idx,stats,err,automatic))
        threading.Thread(target=work,daemon=True).start()

    def built(self,out,idx,stats,err,automatic):
        self.end_busy()
        if err:
            self.status.set(f'Index update failed: {err}')
            if not automatic:messagebox.showerror('Needle',str(err))
        else:
            self.index=idx;self.index_path=Path(out);self.refresh_index_info();self.status.set(f"Index updated: {stats.changed:,} changed, {stats.removed:,} removed.")
        if self.auto.get():self.schedule_auto()

    def search(self):
        if not self.index:messagebox.showinfo('Needle','Open or build an index first.');return
        if self.busy:return
        q=self.query.get();ext=None if self.ext.get()=='All types' else self.ext.get();self.generation+=1;g=self.generation;self.begin_busy('Searching…' if q.strip() else 'Browsing files…')
        def work():
            try:p=self.index.search(q,limit=None,ext=ext);e=None
            except Exception as x:p=None;e=x
            self.root.after(0,lambda:self.searched(g,p,e))
        threading.Thread(target=work,daemon=True).start()

    def searched(self,g,p,e):
        if g!=self.generation:return
        self.end_busy()
        if e:messagebox.showerror('Needle',str(e));self.status.set('Search failed.');return
        self.all_results=p['results'];self.page=0;self.render_page();sugg=p.get('suggestions') or {};suffix=''
        if sugg:suffix=' • typo: '+', '.join(f"{k}→{'/'.join(v)}" for k,v in sugg.items())
        self.status.set(f"{len(self.all_results):,} {'files' if p['mode']=='browse' else 'results'}{suffix}")

    def render_page(self):
        self.results.delete(*self.results.get_children())
        if not self.all_results:return
        a=self.page*self.PAGE_SIZE;b=min(len(self.all_results),a+self.PAGE_SIZE)
        for i,r in enumerate(self.all_results[a:b],a):
            mod=time.strftime('%Y-%m-%d %H:%M',time.localtime(r.get('mtime',0)));score='' if r.get('mode')=='browse' else f"{r.get('score',0):.3f}"
            self.results.insert('', 'end',iid=str(i),values=(r['name'],r.get('ext',''),score,human_bytes(r.get('size',0)),mod,r['path']))
        self.status.set(f"{len(self.all_results):,} results • showing {a+1:,}–{b:,}")

    def selected(self):
        s=self.results.selection()
        if not s:return None
        try:return self.all_results[int(s[0])]
        except:return None

    def select_result(self,_=None):
        r=self.selected()
        if not r:return
        self.detail.configure(text=r['path']);self.snippet.configure(state='normal');self.snippet.delete('1.0','end');self.snippet.insert('1.0',r.get('snippet') or 'No snippet in browse mode.');self.snippet.configure(state='disabled')

    def open_selected(self):
        r=self.selected()
        if r:
            p=native_path(r['path'])
            if p.exists():open_file(p)
            else:messagebox.showerror('Needle',f'File not found:\n{p}')
    def reveal_selected(self):
        r=self.selected()
        if r:
            p=native_path(r['path'])
            if p.exists():reveal_file(p)
    def copy_path(self):
        r=self.selected()
        if r:self.root.clipboard_clear();self.root.clipboard_append(str(native_path(r['path'])));self.status.set('Path copied.')
    def next_page(self):
        if (self.page+1)*self.PAGE_SIZE<len(self.all_results):self.page+=1;self.render_page()
    def prev_page(self):
        if self.page>0:self.page-=1;self.render_page()

    def toggle_auto(self):
        if self.auto.get():
            if not self.index:self.auto.set(False);messagebox.showinfo('Needle','Open an index first.');return
            self.status.set('Auto-update enabled.');self.schedule_auto()
        else:
            if self.auto_job:
                try:self.root.after_cancel(self.auto_job)
                except:pass
            self.auto_job=None;self.status.set('Auto-update disabled.')
    def schedule_auto(self):
        if self.auto_job:
            try:self.root.after_cancel(self.auto_job)
            except:pass
        self.auto_job=self.root.after(60000,self.auto_tick)
    def auto_tick(self):
        self.auto_job=None
        if self.auto.get():self.update_index(automatic=True)

def main():
    root=tk.Tk();App(root);root.mainloop()
if __name__=='__main__':main()
