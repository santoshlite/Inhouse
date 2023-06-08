(function(l, r) { if (!l || l.getElementById('livereloadscript')) return; r = l.createElement('script'); r.async = 1; r.src = '//' + (self.location.host || 'localhost').split(':')[0] + ':35729/livereload.js?snipver=1'; r.id = 'livereloadscript'; l.getElementsByTagName('head')[0].appendChild(r) })(self.document);
var app = (function () {
    'use strict';

    function noop() { }
    function add_location(element, file, line, column, char) {
        element.__svelte_meta = {
            loc: { file, line, column, char }
        };
    }
    function run(fn) {
        return fn();
    }
    function blank_object() {
        return Object.create(null);
    }
    function run_all(fns) {
        fns.forEach(run);
    }
    function is_function(thing) {
        return typeof thing === 'function';
    }
    function safe_not_equal(a, b) {
        return a != a ? b == b : a !== b || ((a && typeof a === 'object') || typeof a === 'function');
    }
    let src_url_equal_anchor;
    function src_url_equal(element_src, url) {
        if (!src_url_equal_anchor) {
            src_url_equal_anchor = document.createElement('a');
        }
        src_url_equal_anchor.href = url;
        return element_src === src_url_equal_anchor.href;
    }
    function is_empty(obj) {
        return Object.keys(obj).length === 0;
    }

    const globals = (typeof window !== 'undefined'
        ? window
        : typeof globalThis !== 'undefined'
            ? globalThis
            : global);
    function append(target, node) {
        target.appendChild(node);
    }
    function insert(target, node, anchor) {
        target.insertBefore(node, anchor || null);
    }
    function detach(node) {
        if (node.parentNode) {
            node.parentNode.removeChild(node);
        }
    }
    function destroy_each(iterations, detaching) {
        for (let i = 0; i < iterations.length; i += 1) {
            if (iterations[i])
                iterations[i].d(detaching);
        }
    }
    function element(name) {
        return document.createElement(name);
    }
    function svg_element(name) {
        return document.createElementNS('http://www.w3.org/2000/svg', name);
    }
    function text(data) {
        return document.createTextNode(data);
    }
    function space() {
        return text(' ');
    }
    function listen(node, event, handler, options) {
        node.addEventListener(event, handler, options);
        return () => node.removeEventListener(event, handler, options);
    }
    function attr(node, attribute, value) {
        if (value == null)
            node.removeAttribute(attribute);
        else if (node.getAttribute(attribute) !== value)
            node.setAttribute(attribute, value);
    }
    function children(element) {
        return Array.from(element.childNodes);
    }
    function set_input_value(input, value) {
        input.value = value == null ? '' : value;
    }
    function set_style(node, key, value, important) {
        if (value == null) {
            node.style.removeProperty(key);
        }
        else {
            node.style.setProperty(key, value, important ? 'important' : '');
        }
    }
    function custom_event(type, detail, { bubbles = false, cancelable = false } = {}) {
        const e = document.createEvent('CustomEvent');
        e.initCustomEvent(type, bubbles, cancelable, detail);
        return e;
    }
    class HtmlTag {
        constructor(is_svg = false) {
            this.is_svg = false;
            this.is_svg = is_svg;
            this.e = this.n = null;
        }
        c(html) {
            this.h(html);
        }
        m(html, target, anchor = null) {
            if (!this.e) {
                if (this.is_svg)
                    this.e = svg_element(target.nodeName);
                /** #7364  target for <template> may be provided as #document-fragment(11) */
                else
                    this.e = element((target.nodeType === 11 ? 'TEMPLATE' : target.nodeName));
                this.t = target.tagName !== 'TEMPLATE' ? target : target.content;
                this.c(html);
            }
            this.i(anchor);
        }
        h(html) {
            this.e.innerHTML = html;
            this.n = Array.from(this.e.nodeName === 'TEMPLATE' ? this.e.content.childNodes : this.e.childNodes);
        }
        i(anchor) {
            for (let i = 0; i < this.n.length; i += 1) {
                insert(this.t, this.n[i], anchor);
            }
        }
        p(html) {
            this.d();
            this.h(html);
            this.i(this.a);
        }
        d() {
            this.n.forEach(detach);
        }
    }

    let current_component;
    function set_current_component(component) {
        current_component = component;
    }
    function get_current_component() {
        if (!current_component)
            throw new Error('Function called outside component initialization');
        return current_component;
    }
    /**
     * The `onMount` function schedules a callback to run as soon as the component has been mounted to the DOM.
     * It must be called during the component's initialisation (but doesn't need to live *inside* the component;
     * it can be called from an external module).
     *
     * `onMount` does not run inside a [server-side component](/docs#run-time-server-side-component-api).
     *
     * https://svelte.dev/docs#run-time-svelte-onmount
     */
    function onMount(fn) {
        get_current_component().$$.on_mount.push(fn);
    }

    const dirty_components = [];
    const binding_callbacks = [];
    let render_callbacks = [];
    const flush_callbacks = [];
    const resolved_promise = /* @__PURE__ */ Promise.resolve();
    let update_scheduled = false;
    function schedule_update() {
        if (!update_scheduled) {
            update_scheduled = true;
            resolved_promise.then(flush);
        }
    }
    function add_render_callback(fn) {
        render_callbacks.push(fn);
    }
    // flush() calls callbacks in this order:
    // 1. All beforeUpdate callbacks, in order: parents before children
    // 2. All bind:this callbacks, in reverse order: children before parents.
    // 3. All afterUpdate callbacks, in order: parents before children. EXCEPT
    //    for afterUpdates called during the initial onMount, which are called in
    //    reverse order: children before parents.
    // Since callbacks might update component values, which could trigger another
    // call to flush(), the following steps guard against this:
    // 1. During beforeUpdate, any updated components will be added to the
    //    dirty_components array and will cause a reentrant call to flush(). Because
    //    the flush index is kept outside the function, the reentrant call will pick
    //    up where the earlier call left off and go through all dirty components. The
    //    current_component value is saved and restored so that the reentrant call will
    //    not interfere with the "parent" flush() call.
    // 2. bind:this callbacks cannot trigger new flush() calls.
    // 3. During afterUpdate, any updated components will NOT have their afterUpdate
    //    callback called a second time; the seen_callbacks set, outside the flush()
    //    function, guarantees this behavior.
    const seen_callbacks = new Set();
    let flushidx = 0; // Do *not* move this inside the flush() function
    function flush() {
        // Do not reenter flush while dirty components are updated, as this can
        // result in an infinite loop. Instead, let the inner flush handle it.
        // Reentrancy is ok afterwards for bindings etc.
        if (flushidx !== 0) {
            return;
        }
        const saved_component = current_component;
        do {
            // first, call beforeUpdate functions
            // and update components
            try {
                while (flushidx < dirty_components.length) {
                    const component = dirty_components[flushidx];
                    flushidx++;
                    set_current_component(component);
                    update(component.$$);
                }
            }
            catch (e) {
                // reset dirty state to not end up in a deadlocked state and then rethrow
                dirty_components.length = 0;
                flushidx = 0;
                throw e;
            }
            set_current_component(null);
            dirty_components.length = 0;
            flushidx = 0;
            while (binding_callbacks.length)
                binding_callbacks.pop()();
            // then, once components are updated, call
            // afterUpdate functions. This may cause
            // subsequent updates...
            for (let i = 0; i < render_callbacks.length; i += 1) {
                const callback = render_callbacks[i];
                if (!seen_callbacks.has(callback)) {
                    // ...so guard against infinite loops
                    seen_callbacks.add(callback);
                    callback();
                }
            }
            render_callbacks.length = 0;
        } while (dirty_components.length);
        while (flush_callbacks.length) {
            flush_callbacks.pop()();
        }
        update_scheduled = false;
        seen_callbacks.clear();
        set_current_component(saved_component);
    }
    function update($$) {
        if ($$.fragment !== null) {
            $$.update();
            run_all($$.before_update);
            const dirty = $$.dirty;
            $$.dirty = [-1];
            $$.fragment && $$.fragment.p($$.ctx, dirty);
            $$.after_update.forEach(add_render_callback);
        }
    }
    /**
     * Useful for example to execute remaining `afterUpdate` callbacks before executing `destroy`.
     */
    function flush_render_callbacks(fns) {
        const filtered = [];
        const targets = [];
        render_callbacks.forEach((c) => fns.indexOf(c) === -1 ? filtered.push(c) : targets.push(c));
        targets.forEach((c) => c());
        render_callbacks = filtered;
    }
    const outroing = new Set();
    let outros;
    function transition_in(block, local) {
        if (block && block.i) {
            outroing.delete(block);
            block.i(local);
        }
    }
    function transition_out(block, local, detach, callback) {
        if (block && block.o) {
            if (outroing.has(block))
                return;
            outroing.add(block);
            outros.c.push(() => {
                outroing.delete(block);
                if (callback) {
                    if (detach)
                        block.d(1);
                    callback();
                }
            });
            block.o(local);
        }
        else if (callback) {
            callback();
        }
    }
    function create_component(block) {
        block && block.c();
    }
    function mount_component(component, target, anchor, customElement) {
        const { fragment, after_update } = component.$$;
        fragment && fragment.m(target, anchor);
        if (!customElement) {
            // onMount happens before the initial afterUpdate
            add_render_callback(() => {
                const new_on_destroy = component.$$.on_mount.map(run).filter(is_function);
                // if the component was destroyed immediately
                // it will update the `$$.on_destroy` reference to `null`.
                // the destructured on_destroy may still reference to the old array
                if (component.$$.on_destroy) {
                    component.$$.on_destroy.push(...new_on_destroy);
                }
                else {
                    // Edge case - component was destroyed immediately,
                    // most likely as a result of a binding initialising
                    run_all(new_on_destroy);
                }
                component.$$.on_mount = [];
            });
        }
        after_update.forEach(add_render_callback);
    }
    function destroy_component(component, detaching) {
        const $$ = component.$$;
        if ($$.fragment !== null) {
            flush_render_callbacks($$.after_update);
            run_all($$.on_destroy);
            $$.fragment && $$.fragment.d(detaching);
            // TODO null out other refs, including component.$$ (but need to
            // preserve final state?)
            $$.on_destroy = $$.fragment = null;
            $$.ctx = [];
        }
    }
    function make_dirty(component, i) {
        if (component.$$.dirty[0] === -1) {
            dirty_components.push(component);
            schedule_update();
            component.$$.dirty.fill(0);
        }
        component.$$.dirty[(i / 31) | 0] |= (1 << (i % 31));
    }
    function init(component, options, instance, create_fragment, not_equal, props, append_styles, dirty = [-1]) {
        const parent_component = current_component;
        set_current_component(component);
        const $$ = component.$$ = {
            fragment: null,
            ctx: [],
            // state
            props,
            update: noop,
            not_equal,
            bound: blank_object(),
            // lifecycle
            on_mount: [],
            on_destroy: [],
            on_disconnect: [],
            before_update: [],
            after_update: [],
            context: new Map(options.context || (parent_component ? parent_component.$$.context : [])),
            // everything else
            callbacks: blank_object(),
            dirty,
            skip_bound: false,
            root: options.target || parent_component.$$.root
        };
        append_styles && append_styles($$.root);
        let ready = false;
        $$.ctx = instance
            ? instance(component, options.props || {}, (i, ret, ...rest) => {
                const value = rest.length ? rest[0] : ret;
                if ($$.ctx && not_equal($$.ctx[i], $$.ctx[i] = value)) {
                    if (!$$.skip_bound && $$.bound[i])
                        $$.bound[i](value);
                    if (ready)
                        make_dirty(component, i);
                }
                return ret;
            })
            : [];
        $$.update();
        ready = true;
        run_all($$.before_update);
        // `false` as a special case of no DOM component
        $$.fragment = create_fragment ? create_fragment($$.ctx) : false;
        if (options.target) {
            if (options.hydrate) {
                const nodes = children(options.target);
                // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                $$.fragment && $$.fragment.l(nodes);
                nodes.forEach(detach);
            }
            else {
                // eslint-disable-next-line @typescript-eslint/no-non-null-assertion
                $$.fragment && $$.fragment.c();
            }
            if (options.intro)
                transition_in(component.$$.fragment);
            mount_component(component, options.target, options.anchor, options.customElement);
            flush();
        }
        set_current_component(parent_component);
    }
    /**
     * Base class for Svelte components. Used when dev=false.
     */
    class SvelteComponent {
        $destroy() {
            destroy_component(this, 1);
            this.$destroy = noop;
        }
        $on(type, callback) {
            if (!is_function(callback)) {
                return noop;
            }
            const callbacks = (this.$$.callbacks[type] || (this.$$.callbacks[type] = []));
            callbacks.push(callback);
            return () => {
                const index = callbacks.indexOf(callback);
                if (index !== -1)
                    callbacks.splice(index, 1);
            };
        }
        $set($$props) {
            if (this.$$set && !is_empty($$props)) {
                this.$$.skip_bound = true;
                this.$$set($$props);
                this.$$.skip_bound = false;
            }
        }
    }

    function dispatch_dev(type, detail) {
        document.dispatchEvent(custom_event(type, Object.assign({ version: '3.59.1' }, detail), { bubbles: true }));
    }
    function append_dev(target, node) {
        dispatch_dev('SvelteDOMInsert', { target, node });
        append(target, node);
    }
    function insert_dev(target, node, anchor) {
        dispatch_dev('SvelteDOMInsert', { target, node, anchor });
        insert(target, node, anchor);
    }
    function detach_dev(node) {
        dispatch_dev('SvelteDOMRemove', { node });
        detach(node);
    }
    function listen_dev(node, event, handler, options, has_prevent_default, has_stop_propagation, has_stop_immediate_propagation) {
        const modifiers = options === true ? ['capture'] : options ? Array.from(Object.keys(options)) : [];
        if (has_prevent_default)
            modifiers.push('preventDefault');
        if (has_stop_propagation)
            modifiers.push('stopPropagation');
        if (has_stop_immediate_propagation)
            modifiers.push('stopImmediatePropagation');
        dispatch_dev('SvelteDOMAddEventListener', { node, event, handler, modifiers });
        const dispose = listen(node, event, handler, options);
        return () => {
            dispatch_dev('SvelteDOMRemoveEventListener', { node, event, handler, modifiers });
            dispose();
        };
    }
    function attr_dev(node, attribute, value) {
        attr(node, attribute, value);
        if (value == null)
            dispatch_dev('SvelteDOMRemoveAttribute', { node, attribute });
        else
            dispatch_dev('SvelteDOMSetAttribute', { node, attribute, value });
    }
    function set_data_dev(text, data) {
        data = '' + data;
        if (text.data === data)
            return;
        dispatch_dev('SvelteDOMSetData', { node: text, data });
        text.data = data;
    }
    function validate_each_argument(arg) {
        if (typeof arg !== 'string' && !(arg && typeof arg === 'object' && 'length' in arg)) {
            let msg = '{#each} only iterates over array-like objects.';
            if (typeof Symbol === 'function' && arg && Symbol.iterator in arg) {
                msg += ' You can use a spread to convert this iterable into an array.';
            }
            throw new Error(msg);
        }
    }
    function validate_slots(name, slot, keys) {
        for (const slot_key of Object.keys(slot)) {
            if (!~keys.indexOf(slot_key)) {
                console.warn(`<${name}> received an unexpected slot "${slot_key}".`);
            }
        }
    }
    /**
     * Base class for Svelte components with some minor dev-enhancements. Used when dev=true.
     */
    class SvelteComponentDev extends SvelteComponent {
        constructor(options) {
            if (!options || (!options.target && !options.$$inline)) {
                throw new Error("'target' is a required option");
            }
            super();
        }
        $destroy() {
            super.$destroy();
            this.$destroy = () => {
                console.warn('Component was already destroyed'); // eslint-disable-line no-console
            };
        }
        $capture_state() { }
        $inject_state() { }
    }

    /* src/lib/History.svelte generated by Svelte v3.59.1 */

    const file$1 = "src/lib/History.svelte";

    function get_each_context$1(ctx, list, i) {
    	const child_ctx = ctx.slice();
    	child_ctx[1] = list[i];
    	return child_ctx;
    }

    // (21:2) {:else}
    function create_else_block(ctx) {
    	let div;

    	const block = {
    		c: function create() {
    			div = element("div");
    			div.textContent = "It's quiet here...";
    			attr_dev(div, "class", "empty-message");
    			add_location(div, file$1, 21, 4, 376);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div, anchor);
    		},
    		p: noop,
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div);
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_else_block.name,
    		type: "else",
    		source: "(21:2) {:else}",
    		ctx
    	});

    	return block;
    }

    // (15:2) {#if hasItems(historyList)}
    function create_if_block$1(ctx) {
    	let div;
    	let each_value = /*historyList*/ ctx[0];
    	validate_each_argument(each_value);
    	let each_blocks = [];

    	for (let i = 0; i < each_value.length; i += 1) {
    		each_blocks[i] = create_each_block$1(get_each_context$1(ctx, each_value, i));
    	}

    	const block = {
    		c: function create() {
    			div = element("div");

    			for (let i = 0; i < each_blocks.length; i += 1) {
    				each_blocks[i].c();
    			}

    			attr_dev(div, "class", "list-container");
    			add_location(div, file$1, 15, 4, 217);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div, anchor);

    			for (let i = 0; i < each_blocks.length; i += 1) {
    				if (each_blocks[i]) {
    					each_blocks[i].m(div, null);
    				}
    			}
    		},
    		p: function update(ctx, dirty) {
    			if (dirty & /*historyList*/ 1) {
    				each_value = /*historyList*/ ctx[0];
    				validate_each_argument(each_value);
    				let i;

    				for (i = 0; i < each_value.length; i += 1) {
    					const child_ctx = get_each_context$1(ctx, each_value, i);

    					if (each_blocks[i]) {
    						each_blocks[i].p(child_ctx, dirty);
    					} else {
    						each_blocks[i] = create_each_block$1(child_ctx);
    						each_blocks[i].c();
    						each_blocks[i].m(div, null);
    					}
    				}

    				for (; i < each_blocks.length; i += 1) {
    					each_blocks[i].d(1);
    				}

    				each_blocks.length = each_value.length;
    			}
    		},
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div);
    			destroy_each(each_blocks, detaching);
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_if_block$1.name,
    		type: "if",
    		source: "(15:2) {#if hasItems(historyList)}",
    		ctx
    	});

    	return block;
    }

    // (17:6) {#each historyList as item}
    function create_each_block$1(ctx) {
    	let div;
    	let t0;
    	let t1_value = /*item*/ ctx[1] + "";
    	let t1;

    	const block = {
    		c: function create() {
    			div = element("div");
    			t0 = text("📄   ");
    			t1 = text(t1_value);
    			attr_dev(div, "class", "history-item");
    			add_location(div, file$1, 17, 8, 288);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div, anchor);
    			append_dev(div, t0);
    			append_dev(div, t1);
    		},
    		p: function update(ctx, dirty) {
    			if (dirty & /*historyList*/ 1 && t1_value !== (t1_value = /*item*/ ctx[1] + "")) set_data_dev(t1, t1_value);
    		},
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div);
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_each_block$1.name,
    		type: "each",
    		source: "(17:6) {#each historyList as item}",
    		ctx
    	});

    	return block;
    }

    function create_fragment$1(ctx) {
    	let div1;
    	let div0;
    	let t1;
    	let show_if;

    	function select_block_type(ctx, dirty) {
    		if (dirty & /*historyList*/ 1) show_if = null;
    		if (show_if == null) show_if = !!hasItems(/*historyList*/ ctx[0]);
    		if (show_if) return create_if_block$1;
    		return create_else_block;
    	}

    	let current_block_type = select_block_type(ctx, -1);
    	let if_block = current_block_type(ctx);

    	const block = {
    		c: function create() {
    			div1 = element("div");
    			div0 = element("div");
    			div0.textContent = "History";
    			t1 = space();
    			if_block.c();
    			attr_dev(div0, "class", "title");
    			add_location(div0, file$1, 12, 2, 149);
    			attr_dev(div1, "class", "wrapper");
    			add_location(div1, file$1, 11, 0, 125);
    		},
    		l: function claim(nodes) {
    			throw new Error("options.hydrate only works if the component was compiled with the `hydratable: true` option");
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div1, anchor);
    			append_dev(div1, div0);
    			append_dev(div1, t1);
    			if_block.m(div1, null);
    		},
    		p: function update(ctx, [dirty]) {
    			if (current_block_type === (current_block_type = select_block_type(ctx, dirty)) && if_block) {
    				if_block.p(ctx, dirty);
    			} else {
    				if_block.d(1);
    				if_block = current_block_type(ctx);

    				if (if_block) {
    					if_block.c();
    					if_block.m(div1, null);
    				}
    			}
    		},
    		i: noop,
    		o: noop,
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div1);
    			if_block.d();
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_fragment$1.name,
    		type: "component",
    		source: "",
    		ctx
    	});

    	return block;
    }

    function hasItems(list) {
    	return list && list.length > 0;
    }

    function instance$1($$self, $$props, $$invalidate) {
    	let { $$slots: slots = {}, $$scope } = $$props;
    	validate_slots('History', slots, []);
    	let { historyList = [] } = $$props;
    	const writable_props = ['historyList'];

    	Object.keys($$props).forEach(key => {
    		if (!~writable_props.indexOf(key) && key.slice(0, 2) !== '$$' && key !== 'slot') console.warn(`<History> was created with unknown prop '${key}'`);
    	});

    	$$self.$$set = $$props => {
    		if ('historyList' in $$props) $$invalidate(0, historyList = $$props.historyList);
    	};

    	$$self.$capture_state = () => ({ historyList, hasItems });

    	$$self.$inject_state = $$props => {
    		if ('historyList' in $$props) $$invalidate(0, historyList = $$props.historyList);
    	};

    	if ($$props && "$$inject" in $$props) {
    		$$self.$inject_state($$props.$$inject);
    	}

    	return [historyList];
    }

    class History extends SvelteComponentDev {
    	constructor(options) {
    		super(options);
    		init(this, options, instance$1, create_fragment$1, safe_not_equal, { historyList: 0 });

    		dispatch_dev("SvelteRegisterComponent", {
    			component: this,
    			tagName: "History",
    			options,
    			id: create_fragment$1.name
    		});
    	}

    	get historyList() {
    		throw new Error("<History>: Props cannot be read directly from the component instance unless compiling with 'accessors: true' or '<svelte:options accessors/>'");
    	}

    	set historyList(value) {
    		throw new Error("<History>: Props cannot be set directly on the component instance unless compiling with 'accessors: true' or '<svelte:options accessors/>'");
    	}
    }

    /* src/App.svelte generated by Svelte v3.59.1 */

    const { console: console_1 } = globals;
    const file = "src/App.svelte";

    function get_each_context(ctx, list, i) {
    	const child_ctx = ctx.slice();
    	child_ctx[24] = list[i];
    	return child_ctx;
    }

    // (242:6) {#if showInputBox}
    function create_if_block(ctx) {
    	let div;
    	let input;
    	let t0;
    	let button;
    	let mounted;
    	let dispose;

    	const block = {
    		c: function create() {
    			div = element("div");
    			input = element("input");
    			t0 = space();
    			button = element("button");
    			button.textContent = "Sync";
    			attr_dev(input, "type", "text");
    			attr_dev(input, "placeholder", "Share link to a folder...");
    			add_location(input, file, 243, 8, 6460);
    			add_location(button, file, 244, 8, 6552);
    			add_location(div, file, 242, 6, 6446);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div, anchor);
    			append_dev(div, input);
    			set_input_value(input, /*urlGoogle*/ ctx[7]);
    			append_dev(div, t0);
    			append_dev(div, button);

    			if (!mounted) {
    				dispose = [
    					listen_dev(input, "input", /*input_input_handler*/ ctx[15]),
    					listen_dev(button, "click", /*uploadGoogle*/ ctx[10], false, false, false, false)
    				];

    				mounted = true;
    			}
    		},
    		p: function update(ctx, dirty) {
    			if (dirty & /*urlGoogle*/ 128 && input.value !== /*urlGoogle*/ ctx[7]) {
    				set_input_value(input, /*urlGoogle*/ ctx[7]);
    			}
    		},
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div);
    			mounted = false;
    			run_all(dispose);
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_if_block.name,
    		type: "if",
    		source: "(242:6) {#if showInputBox}",
    		ctx
    	});

    	return block;
    }

    // (253:8) {#each blocksList as block}
    function create_each_block(ctx) {
    	let div1;
    	let div0;
    	let html_tag;
    	let raw_value = /*block*/ ctx[24].tag + "";
    	let t0;
    	let p0;
    	let t1_value = /*block*/ ctx[24].document_name + "";
    	let t1;
    	let t2;
    	let p1;
    	let t3_value = /*block*/ ctx[24].block + "";
    	let t3;
    	let t4;

    	const block = {
    		c: function create() {
    			div1 = element("div");
    			div0 = element("div");
    			html_tag = new HtmlTag(false);
    			t0 = space();
    			p0 = element("p");
    			t1 = text(t1_value);
    			t2 = space();
    			p1 = element("p");
    			t3 = text(t3_value);
    			t4 = space();
    			html_tag.a = t0;
    			attr_dev(p0, "class", "docname");
    			add_location(p0, file, 256, 12, 6952);
    			attr_dev(div0, "class", "title-tag");
    			add_location(div0, file, 254, 10, 6885);
    			add_location(p1, file, 258, 8, 7022);
    			attr_dev(div1, "class", "wrapper-block");
    			add_location(div1, file, 253, 8, 6847);
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div1, anchor);
    			append_dev(div1, div0);
    			html_tag.m(raw_value, div0);
    			append_dev(div0, t0);
    			append_dev(div0, p0);
    			append_dev(p0, t1);
    			append_dev(div1, t2);
    			append_dev(div1, p1);
    			append_dev(p1, t3);
    			append_dev(div1, t4);
    		},
    		p: function update(ctx, dirty) {
    			if (dirty & /*blocksList*/ 8 && raw_value !== (raw_value = /*block*/ ctx[24].tag + "")) html_tag.p(raw_value);
    			if (dirty & /*blocksList*/ 8 && t1_value !== (t1_value = /*block*/ ctx[24].document_name + "")) set_data_dev(t1, t1_value);
    			if (dirty & /*blocksList*/ 8 && t3_value !== (t3_value = /*block*/ ctx[24].block + "")) set_data_dev(t3, t3_value);
    		},
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div1);
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_each_block.name,
    		type: "each",
    		source: "(253:8) {#each blocksList as block}",
    		ctx
    	});

    	return block;
    }

    function create_fragment(ctx) {
    	let div0;
    	let history;
    	let t0;
    	let div8;
    	let div6;
    	let h1;
    	let t2;
    	let div2;
    	let div1;
    	let input0;
    	let t3;
    	let button;
    	let t5;
    	let div5;
    	let div3;
    	let label0;
    	let t6;
    	let input1;
    	let t7;
    	let div4;
    	let label1;
    	let img;
    	let img_src_value;
    	let t8;
    	let input2;
    	let t9;
    	let t10;
    	let p0;
    	let t11;
    	let t12;
    	let div7;
    	let p1;
    	let b;
    	let t13;
    	let html_tag;
    	let t14;
    	let current;
    	let mounted;
    	let dispose;

    	history = new History({
    			props: {
    				historyList: /*historylist*/ ctx[4],
    				fetchResponse: /*fetchResponse*/ ctx[11]
    			},
    			$$inline: true
    		});

    	let if_block = /*showInputBox*/ ctx[6] && create_if_block(ctx);
    	let each_value = /*blocksList*/ ctx[3];
    	validate_each_argument(each_value);
    	let each_blocks = [];

    	for (let i = 0; i < each_value.length; i += 1) {
    		each_blocks[i] = create_each_block(get_each_context(ctx, each_value, i));
    	}

    	const block = {
    		c: function create() {
    			div0 = element("div");
    			create_component(history.$$.fragment);
    			t0 = space();
    			div8 = element("div");
    			div6 = element("div");
    			h1 = element("h1");
    			h1.textContent = "inhouse 🏠";
    			t2 = space();
    			div2 = element("div");
    			div1 = element("div");
    			input0 = element("input");
    			t3 = space();
    			button = element("button");
    			button.textContent = "🔍";
    			t5 = space();
    			div5 = element("div");
    			div3 = element("div");
    			label0 = element("label");
    			t6 = text("📥    Upload\n            ");
    			input1 = element("input");
    			t7 = space();
    			div4 = element("div");
    			label1 = element("label");
    			img = element("img");
    			t8 = text("   Sync Drive\n            ");
    			input2 = element("input");
    			t9 = space();
    			if (if_block) if_block.c();
    			t10 = space();
    			p0 = element("p");
    			t11 = text(/*indexedInfo*/ ctx[2]);
    			t12 = space();
    			div7 = element("div");
    			p1 = element("p");
    			b = element("b");
    			t13 = text(/*question*/ ctx[5]);
    			html_tag = new HtmlTag(false);
    			t14 = space();

    			for (let i = 0; i < each_blocks.length; i += 1) {
    				each_blocks[i].c();
    			}

    			attr_dev(div0, "class", "row");
    			add_location(div0, file, 212, 0, 5252);
    			add_location(h1, file, 218, 8, 5413);
    			attr_dev(input0, "placeholder", "Ask a question.");
    			attr_dev(input0, "class", "searchbar");
    			attr_dev(input0, "type", "text");
    			add_location(input0, file, 221, 12, 5524);
    			attr_dev(button, "class", "submit-button");
    			add_location(button, file, 222, 12, 5656);
    			attr_dev(div1, "class", "input-container");
    			add_location(div1, file, 220, 10, 5482);
    			attr_dev(div2, "class", "search-container");
    			add_location(div2, file, 219, 8, 5441);
    			attr_dev(input1, "id", "fileInput");
    			attr_dev(input1, "type", "file");
    			set_style(input1, "display", "none");
    			input1.multiple = true;
    			add_location(input1, file, 230, 12, 5925);
    			attr_dev(label0, "for", "fileInput");
    			attr_dev(label0, "class", "upload-button");
    			add_location(label0, file, 228, 10, 5835);
    			attr_dev(div3, "class", "upload-button-container");
    			add_location(div3, file, 227, 8, 5787);
    			if (!src_url_equal(img.src, img_src_value = "https://upload.wikimedia.org/wikipedia/commons/1/12/Google_Drive_icon_%282020%29.svg")) attr_dev(img, "src", img_src_value);
    			attr_dev(img, "alt", "google drive icon");
    			add_location(img, file, 236, 12, 6154);
    			attr_dev(input2, "type", "text");
    			set_style(input2, "display", "none");
    			add_location(input2, file, 237, 12, 6308);
    			attr_dev(label1, "class", "gdrive-button");
    			add_location(label1, file, 235, 10, 6112);
    			attr_dev(div4, "class", "gdrive-button-container");
    			add_location(div4, file, 234, 8, 6064);
    			attr_dev(div5, "class", "uploads");
    			add_location(div5, file, 226, 8, 5757);
    			attr_dev(p0, "class", "custom-i");
    			add_location(p0, file, 247, 8, 6629);
    			attr_dev(div6, "class", "top-bar");
    			add_location(div6, file, 217, 6, 5383);
    			attr_dev(b, "class", "query");
    			add_location(b, file, 251, 28, 6746);
    			html_tag.a = null;
    			attr_dev(p1, "class", "response");
    			add_location(p1, file, 251, 8, 6726);
    			attr_dev(div7, "class", "wrapper-response");
    			add_location(div7, file, 250, 6, 6687);
    			attr_dev(div8, "class", "row-bar");
    			add_location(div8, file, 216, 4, 5355);
    		},
    		l: function claim(nodes) {
    			throw new Error("options.hydrate only works if the component was compiled with the `hydratable: true` option");
    		},
    		m: function mount(target, anchor) {
    			insert_dev(target, div0, anchor);
    			mount_component(history, div0, null);
    			insert_dev(target, t0, anchor);
    			insert_dev(target, div8, anchor);
    			append_dev(div8, div6);
    			append_dev(div6, h1);
    			append_dev(div6, t2);
    			append_dev(div6, div2);
    			append_dev(div2, div1);
    			append_dev(div1, input0);
    			set_input_value(input0, /*inputValue*/ ctx[0]);
    			append_dev(div1, t3);
    			append_dev(div1, button);
    			append_dev(div6, t5);
    			append_dev(div6, div5);
    			append_dev(div5, div3);
    			append_dev(div3, label0);
    			append_dev(label0, t6);
    			append_dev(label0, input1);
    			append_dev(div5, t7);
    			append_dev(div5, div4);
    			append_dev(div4, label1);
    			append_dev(label1, img);
    			append_dev(label1, t8);
    			append_dev(label1, input2);
    			append_dev(div6, t9);
    			if (if_block) if_block.m(div6, null);
    			append_dev(div6, t10);
    			append_dev(div6, p0);
    			append_dev(p0, t11);
    			append_dev(div8, t12);
    			append_dev(div8, div7);
    			append_dev(div7, p1);
    			append_dev(p1, b);
    			append_dev(b, t13);
    			html_tag.m(/*responseValue*/ ctx[1], p1);
    			append_dev(div7, t14);

    			for (let i = 0; i < each_blocks.length; i += 1) {
    				if (each_blocks[i]) {
    					each_blocks[i].m(div7, null);
    				}
    			}

    			current = true;

    			if (!mounted) {
    				dispose = [
    					listen_dev(input0, "input", /*input0_input_handler*/ ctx[14]),
    					listen_dev(input0, "keydown", /*handleKeyDown*/ ctx[12], false, false, false, false),
    					listen_dev(button, "click", /*search*/ ctx[8], false, false, false, false),
    					listen_dev(input1, "change", /*handleFileChange*/ ctx[13], false, false, false, false),
    					listen_dev(input2, "click", /*askUrl*/ ctx[9], false, false, false, false)
    				];

    				mounted = true;
    			}
    		},
    		p: function update(ctx, [dirty]) {
    			const history_changes = {};
    			if (dirty & /*historylist*/ 16) history_changes.historyList = /*historylist*/ ctx[4];
    			history.$set(history_changes);

    			if (dirty & /*inputValue*/ 1 && input0.value !== /*inputValue*/ ctx[0]) {
    				set_input_value(input0, /*inputValue*/ ctx[0]);
    			}

    			if (/*showInputBox*/ ctx[6]) {
    				if (if_block) {
    					if_block.p(ctx, dirty);
    				} else {
    					if_block = create_if_block(ctx);
    					if_block.c();
    					if_block.m(div6, t10);
    				}
    			} else if (if_block) {
    				if_block.d(1);
    				if_block = null;
    			}

    			if (!current || dirty & /*indexedInfo*/ 4) set_data_dev(t11, /*indexedInfo*/ ctx[2]);
    			if (!current || dirty & /*question*/ 32) set_data_dev(t13, /*question*/ ctx[5]);
    			if (!current || dirty & /*responseValue*/ 2) html_tag.p(/*responseValue*/ ctx[1]);

    			if (dirty & /*blocksList*/ 8) {
    				each_value = /*blocksList*/ ctx[3];
    				validate_each_argument(each_value);
    				let i;

    				for (i = 0; i < each_value.length; i += 1) {
    					const child_ctx = get_each_context(ctx, each_value, i);

    					if (each_blocks[i]) {
    						each_blocks[i].p(child_ctx, dirty);
    					} else {
    						each_blocks[i] = create_each_block(child_ctx);
    						each_blocks[i].c();
    						each_blocks[i].m(div7, null);
    					}
    				}

    				for (; i < each_blocks.length; i += 1) {
    					each_blocks[i].d(1);
    				}

    				each_blocks.length = each_value.length;
    			}
    		},
    		i: function intro(local) {
    			if (current) return;
    			transition_in(history.$$.fragment, local);
    			current = true;
    		},
    		o: function outro(local) {
    			transition_out(history.$$.fragment, local);
    			current = false;
    		},
    		d: function destroy(detaching) {
    			if (detaching) detach_dev(div0);
    			destroy_component(history);
    			if (detaching) detach_dev(t0);
    			if (detaching) detach_dev(div8);
    			if (if_block) if_block.d();
    			destroy_each(each_blocks, detaching);
    			mounted = false;
    			run_all(dispose);
    		}
    	};

    	dispatch_dev("SvelteRegisterBlock", {
    		block,
    		id: create_fragment.name,
    		type: "component",
    		source: "",
    		ctx
    	});

    	return block;
    }

    function scrollToNextSpan(spanId) {
    	const spanElements = document.getElementsByClassName('one');
    	const currentIndex = Array.from(spanElements).findIndex(span => span.id === spanId);

    	if (currentIndex !== -1) {
    		const nextIndex = currentIndex + 1;

    		if (nextIndex < spanElements.length) {
    			const nextSpan = spanElements[nextIndex];
    			nextSpan.scrollIntoView({ behavior: 'smooth' });
    		}
    	}
    }

    function instance($$self, $$props, $$invalidate) {
    	let { $$slots: slots = {}, $$scope } = $$props;
    	validate_slots('App', slots, []);
    	let inputValue = "";
    	let responseValue = "Ready to take your questions!";
    	let indexedInfo = "";
    	let token = "";
    	let blocksList = [];
    	let historylist = [];
    	let fileInput;
    	let question = "";
    	let showInputBox = false;
    	let urlGoogle;

    	async function getHistoryList() {
    		const response = await fetch(`./get_history_list/${token}`);
    		const data = await response.json();

    		if (response.ok) {
    			$$invalidate(4, historylist = data.queries);
    		} else {
    			$$invalidate(4, historylist = ["Could not load history"]);
    		}
    	}

    	async function getTokenFromUrl() {
    		const path = window.location.pathname;
    		const parts = path.split("/");
    		const lastPart = parts[parts.length - 1];
    		token = lastPart;
    	}

    	async function getUploadedItems() {
    		const response = await fetch(`./get_uploaded_count/${token}`);
    		const data = await response.text();
    		return data;
    	}

    	async function fetchData() {
    		const count = await getUploadedItems();

    		if (count === "0") {
    			$$invalidate(2, indexedInfo = "Upload files to get started!");
    			return;
    		} else if (count === "1") {
    			$$invalidate(2, indexedInfo = count + " file indexed");
    			return;
    		}

    		$$invalidate(2, indexedInfo = count + " files indexed.");
    	}

    	async function search() {
    		if (inputValue === "") {
    			$$invalidate(1, responseValue = "No text :(");
    			return;
    		} else if (indexedInfo === "Upload files to get started!") {
    			$$invalidate(1, responseValue = "Upload files first");
    			return;
    		}

    		$$invalidate(5, question = "");
    		$$invalidate(1, responseValue = "Waiting for the LLM...");
    		$$invalidate(3, blocksList = []);

    		const response = await fetch(`./search/${token}`, {
    			method: 'POST',
    			headers: { 'Content-Type': 'application/json' },
    			body: JSON.stringify({ value: inputValue })
    		});

    		const data = await response.json();
    		console.log(data);
    		$$invalidate(5, question = "Q: " + inputValue);
    		$$invalidate(1, responseValue = data.result);
    		$$invalidate(3, blocksList = data.blocks);
    		console.log(blocksList);
    		await getHistoryList();
    	}

    	async function askUrl() {
    		$$invalidate(6, showInputBox = true);
    	}

    	async function uploadGoogle() {
    		$$invalidate(6, showInputBox = false);

    		if (urlGoogle === "") {
    			$$invalidate(2, indexedInfo = "URL is empty :(");
    			return;
    		}

    		$$invalidate(2, indexedInfo = "Loading your Google Drive folder...");

    		const response = await fetch(`./upload_google_file/${token}`, {
    			method: 'POST',
    			headers: { 'Content-Type': 'application/json' },
    			body: JSON.stringify({ url: urlGoogle })
    		});

    		const data = await response.json();
    		const count = await getUploadedItems();
    		$$invalidate(2, indexedInfo = data.Message + " " + count + " indexed.");
    		await getHistoryList();
    	}

    	async function uploadFile() {
    		$$invalidate(2, indexedInfo = "Uploading...");
    		const formData = new FormData();
    		const allowedFileTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/svg+xml', 'image/webp'];
    		let unsupportedFiles = [];

    		for (let i = 0; i < fileInput.files.length; i++) {
    			if (allowedFileTypes.includes(fileInput.files[i].type)) {
    				unsupportedFiles.push(fileInput.files[i].name);
    				continue;
    			}

    			formData.append('files[]', fileInput.files[i]);
    		}

    		const response = await fetch(`./upload_file/${token}`, { method: 'POST', body: formData });

    		if (unsupportedFiles.length > 0) {
    			const warningMessage = `Could not upload the following files. Image type files are not allowed: ${unsupportedFiles.join(', ')}`;
    			alert(warningMessage);
    		}

    		await response.json();
    		fetchData();
    	}

    	async function fetchResponse(query) {
    		const response = await fetch(`./get_response_from_query/${token}`, {
    			method: 'POST',
    			headers: { 'Content-Type': 'application/json' },
    			body: JSON.stringify({ value: query })
    		});

    		if (response.ok) {
    			const data = await response.json();
    			$$invalidate(1, responseValue = data.result);
    			$$invalidate(5, question = "Q: " + data.query);
    			$$invalidate(3, blocksList = data.blocks);
    		} else {
    			$$invalidate(1, responseValue = "Error fetching response.");
    		}
    	}

    	function handleKeyDown(event) {
    		if (event.key === "Enter") {
    			search();
    		}
    	}

    	function handleFileChange(event) {
    		fileInput = event.target;
    		uploadFile();
    	}

    	async function syncGoogle() {
    		$$invalidate(2, indexedInfo = "Syncing with Google Drive...");
    		const response = await fetch(`https://inhouse.up.railway.app/app/sync_google/${token}`);
    		const data = await response.json();

    		if (data.Message === "X") {
    			console.log("here");
    			await fetchData();
    		} else {
    			const count = await getUploadedItems();
    			$$invalidate(2, indexedInfo = data.Message + ". " + count + " indexed.");
    		}

    		return data;
    	}

    	onMount(async () => {
    		await getTokenFromUrl();
    		await fetchData();
    		await getHistoryList();
    		await syncGoogle();
    	});

    	const writable_props = [];

    	Object.keys($$props).forEach(key => {
    		if (!~writable_props.indexOf(key) && key.slice(0, 2) !== '$$' && key !== 'slot') console_1.warn(`<App> was created with unknown prop '${key}'`);
    	});

    	function input0_input_handler() {
    		inputValue = this.value;
    		$$invalidate(0, inputValue);
    	}

    	function input_input_handler() {
    		urlGoogle = this.value;
    		$$invalidate(7, urlGoogle);
    	}

    	$$self.$capture_state = () => ({
    		onMount,
    		History,
    		inputValue,
    		responseValue,
    		indexedInfo,
    		token,
    		blocksList,
    		historylist,
    		fileInput,
    		question,
    		showInputBox,
    		urlGoogle,
    		getHistoryList,
    		getTokenFromUrl,
    		getUploadedItems,
    		fetchData,
    		search,
    		askUrl,
    		uploadGoogle,
    		uploadFile,
    		fetchResponse,
    		handleKeyDown,
    		handleFileChange,
    		syncGoogle,
    		scrollToNextSpan
    	});

    	$$self.$inject_state = $$props => {
    		if ('inputValue' in $$props) $$invalidate(0, inputValue = $$props.inputValue);
    		if ('responseValue' in $$props) $$invalidate(1, responseValue = $$props.responseValue);
    		if ('indexedInfo' in $$props) $$invalidate(2, indexedInfo = $$props.indexedInfo);
    		if ('token' in $$props) token = $$props.token;
    		if ('blocksList' in $$props) $$invalidate(3, blocksList = $$props.blocksList);
    		if ('historylist' in $$props) $$invalidate(4, historylist = $$props.historylist);
    		if ('fileInput' in $$props) fileInput = $$props.fileInput;
    		if ('question' in $$props) $$invalidate(5, question = $$props.question);
    		if ('showInputBox' in $$props) $$invalidate(6, showInputBox = $$props.showInputBox);
    		if ('urlGoogle' in $$props) $$invalidate(7, urlGoogle = $$props.urlGoogle);
    	};

    	if ($$props && "$$inject" in $$props) {
    		$$self.$inject_state($$props.$$inject);
    	}

    	return [
    		inputValue,
    		responseValue,
    		indexedInfo,
    		blocksList,
    		historylist,
    		question,
    		showInputBox,
    		urlGoogle,
    		search,
    		askUrl,
    		uploadGoogle,
    		fetchResponse,
    		handleKeyDown,
    		handleFileChange,
    		input0_input_handler,
    		input_input_handler
    	];
    }

    class App extends SvelteComponentDev {
    	constructor(options) {
    		super(options);
    		init(this, options, instance, create_fragment, safe_not_equal, {});

    		dispatch_dev("SvelteRegisterComponent", {
    			component: this,
    			tagName: "App",
    			options,
    			id: create_fragment.name
    		});
    	}
    }

    const app = new App({
    	target: document.body,
    	props: {
    		name: 'world'
    	}
    });

    return app;

})();
//# sourceMappingURL=bundle.js.map
