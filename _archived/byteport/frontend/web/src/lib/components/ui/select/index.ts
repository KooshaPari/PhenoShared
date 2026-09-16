// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-nocheck
import { Select as SelectPrimitive } from 'bits-ui';

import Label from './select-label.svelte';
import Item from './select-item.svelte';
import Content from './select-content.svelte';
import Trigger from './select-trigger.svelte';
import Separator from './select-separator.svelte';

const Root = SelectPrimitive.Root;
const Group = SelectPrimitive.Group;
const Value = SelectPrimitive.Value;

export {
	Root,
	Group,
	Label,
	Item,
	Value,
	Content,
	Trigger,
	Separator,
	//
	Root as Select,
	Group as SelectGroup,
	Label as SelectLabel,
	Item as SelectItem,
	Value as SelectValue,
	Content as SelectContent,
	Trigger as SelectTrigger,
	Separator as SelectSeparator
};
